import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { APIRequestContext, Browser, BrowserContext, Page, Route } from "@playwright/test";
import {
	createFolder,
	type DriveNode,
	purgeNode,
	trashNode,
	waitForChild,
} from "../drive-backed-apps/helpers/drive";
import { loginViaApi, type Credentials } from "../shared/auth";

const VIEWPORT = { width: 1440, height: 900 };
/** Enough for frappe-ui transitions and the 180 ms skeleton delay to finish. */
const SETTLE_MS = 450;
export const WORKSPACE_FOLDER = "UI states";

/**
 * A request hold: traffic matching the pattern waits until the hold ends.
 * `abort` fails the held requests and every later match, since the transport
 * retries server errors, until `release` lets traffic through again.
 */
export interface Hold {
	release(): Promise<void>;
	abort(status?: number): Promise<void>;
}

export interface People {
	/** Owns the content the flows create. */
	actor: Credentials;
	/** Receives shares; shares things back. */
	peer: Credentials;
	/** Never touched, so My files, Recent and Trash stay empty. */
	fresh: Credentials;
}

/**
 * One browser session in one capture path: signed in as the actor, with a
 * folder of its own under `UI states` in My files, so paths never see each
 * other's rows.
 */
export interface Scene {
	page: Page;
	context: BrowserContext;
	api: APIRequestContext;
	baseURL: string;
	people: People;
	/** The actor's Personal root. */
	root: string;
	/** This path's own folder, purged when the scene closes. Empty until the flow fills it. */
	folder: DriveNode;
	/** A name unique to this path. */
	name(label: string): string;
	goto(path: string): Promise<void>;
	/** Holds requests whose URL matches until released or aborted. */
	hold(url: string | RegExp): Promise<Hold>;
	/** Waits for transitions and the skeleton delay. */
	settle(ms?: number): Promise<void>;
	/** Signs in as another user in a second context, for shares and reactions. */
	as(user: Credentials): Promise<APIRequestContext>;
	close(): Promise<void>;
}

const statePath = resolve(__dirname, "../drive-backed-apps/.state/run.json");

export function people(): People {
	const run = JSON.parse(readFileSync(statePath, "utf8")) as { users: Credentials[] };
	const [actor, peer, fresh] = run.users;
	if (!actor || !peer || !fresh) throw new Error("ui-states needs three provisioned users");
	return { actor, peer, fresh };
}

let workspace: Promise<string> | null = null;

/** The `UI states` folder under the actor's root, created once per run. */
function workspaceFolder(api: APIRequestContext, root: string): Promise<string> {
	workspace ??= (async () => {
		const rows = await api.get(`/api/suite/drive/nodes/${root}/children`);
		const { data } = (await rows.json()) as { data: { rows: DriveNode[] } };
		const found = data.rows.find((row) => row.title === WORKSPACE_FOLDER);
		return found?.name ?? (await createFolder(api, WORKSPACE_FOLDER, root)).name;
	})();
	return workspace;
}

export async function openScene(
	browser: Browser,
	baseURL: string,
	folderTitle: string,
): Promise<Scene> {
	const who = people();
	const context = await browser.newContext({ baseURL, viewport: VIEWPORT, colorScheme: "light" });
	const api = context.request;
	await loginViaApi(api, who.actor);
	const roots = await api.get("/api/suite/drive/roots");
	const { data } = (await roots.json()) as { data: { personal: { node: string } } };
	const root = data.personal.node;
	const parent = await workspaceFolder(api, root);
	const stamp = Date.now().toString(36);
	const folder = await createFolder(api, folderTitle, parent);
	const page = await context.newPage();
	const others: BrowserContext[] = [];

	return {
		page,
		context,
		api,
		baseURL,
		people: who,
		root,
		folder,
		name: (label) => `${label} ${stamp}`,
		async goto(path) {
			await page.goto(path);
		},
		async hold(url) {
			// The handler stays routed for the scene's life: unrouting lets a held request through.
			const held: Route[] = [];
			let status: number | null = null;
			let passing = false;
			const fail = (route: Route) =>
				route.fulfill({
					status: status ?? 500,
					contentType: "application/json",
					body: JSON.stringify({ exc_type: "ServerError", message: "Something went wrong" }),
				});
			await page.route(url, async (route) => {
				if (passing) await route.continue();
				else if (status === null) held.push(route);
				else await fail(route);
			});
			return {
				async release() {
					passing = true;
					await Promise.all(held.splice(0).map((route) => route.continue().catch(() => undefined)));
				},
				async abort(next = 500) {
					status = next;
					await Promise.all(held.splice(0).map((route) => fail(route).catch(() => undefined)));
				},
			};
		},
		async settle(ms = SETTLE_MS) {
			await page.waitForTimeout(ms);
		},
		async as(user) {
			const other = await browser.newContext({ baseURL });
			others.push(other);
			await loginViaApi(other.request, user);
			return other.request;
		},
		async close() {
			await Promise.all(others.map((other) => other.close()));
			await trashNode(api, folder.name);
			await purgeNode(api, folder.name);
			await context.close();
		},
	};
}

export { waitForChild };
