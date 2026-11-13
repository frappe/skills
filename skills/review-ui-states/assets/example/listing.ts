// Example from a Frappe app's Drive module: its imports and API paths are that app's.
// Copy the shape, not the code.
import { expect } from "@playwright/test";
import { setup } from "xstate";
import { fillFolder, folderPath, type FolderContent } from "../content";
import { defineFlow } from "../flow";
import { row } from "../../drive-backed-apps/helpers/drive";
import type { Hold, Scene } from "../scene";

type Event =
	| { type: "LOADS" }
	| { type: "FAILS" }
	| { type: "RETRY" }
	| { type: "SEARCH" }
	| { type: "SEARCH_MISS" }
	| { type: "CLEAR_SEARCH" }
	| { type: "FILTER" }
	| { type: "FILTER_MISS" }
	| { type: "CLEAR_FILTER" }
	| { type: "RESORT" }
	| { type: "SETTLES" }
	| { type: "OPEN_EMPTY" };

/**
 * A folder listing from the first paint to its empty, failed, searched,
 * filtered and re-sorted forms. In the code this is spread over
 * `FilesListing.vue`'s v-if chain (`isBlank`, error, empty, rows),
 * `heldWhileRearranging`, `useSkeletonDelay`, `emptyState()` and the `q` and
 * `type` route queries.
 */
const machine = setup({ types: { events: {} as Event } }).createMachine({
	id: "listing",
	initial: "blank",
	states: {
		blank: {
			meta: { description: "First 180 ms of a load: nothing shown, so a fast load never flashes a skeleton.", transient: true },
			always: "skeleton",
		},
		skeleton: {
			meta: { description: "Rows still loading after 180 ms: skeleton rows under the real header." },
			on: { LOADS: "populated", FAILS: "failed" },
		},
		failed: {
			meta: { description: "The listing request failed: the server's message and a Retry button." },
			on: { RETRY: "populated" },
		},
		populated: {
			meta: { description: "Folders first, then files, with the columns the user keeps." },
			on: {
				SEARCH: "searchResults",
				SEARCH_MISS: "searchEmpty",
				FILTER: "filtered",
				FILTER_MISS: "filteredEmpty",
				RESORT: "rearranging",
				OPEN_EMPTY: "empty",
			},
		},
		empty: {
			meta: { description: "A folder with nothing in it, with the hint to use New." },
		},
		searchResults: {
			meta: { description: "Search across all files: each row shows where it lives." },
			on: { CLEAR_SEARCH: "populated" },
		},
		searchEmpty: {
			meta: { description: "A search term nothing matches." },
			on: { CLEAR_SEARCH: "populated" },
		},
		filtered: {
			meta: { description: "One type kept, named in the filter control." },
			on: { CLEAR_FILTER: "populated" },
		},
		filteredEmpty: {
			meta: { description: "A type filter nothing here matches, with Clear filter in the empty state." },
			on: { CLEAR_FILTER: "populated" },
		},
		rearranging: {
			meta: { description: "The old rows stay while a new sort loads, so the user keeps their place." },
			on: { SETTLES: "populated" },
		},
	},
});

const content = new WeakMap<Scene, FolderContent>();
const holds = new WeakMap<Scene, Hold>();

function childrenOf(scene: Scene): string {
	return `**/api/suite/drive/nodes/${scene.folder.name}/children*`;
}

async function expectRows(scene: Scene): Promise<void> {
	await expect(scene.page.getByRole("button", { name: /^Actions for / }).first()).toBeVisible();
}

function typeFilter(scene: Scene) {
	return scene.page.getByRole("button", { name: /^Filter by/ });
}

export const listing = defineFlow<Event>({
	id: "listing",
	title: "Folder listing",
	folderTitle: "Website relaunch",
	source: "frontend/src/apps/drive/files/features/FilesListing.vue",
	machine,
	async enter(scene) {
		content.set(scene, await fillFolder(scene.api, scene.folder.name));
		holds.set(scene, await scene.hold(childrenOf(scene)));
		await scene.goto(folderPath(scene.folder));
	},
	settle: {
		// The shell's own boot splash comes first; the skeleton is the listing's.
		async skeleton(scene) {
			await expect(scene.page.getByRole("searchbox", { name: "Search all files" })).toBeVisible();
		},
	},
	events: {
		async LOADS(scene) {
			await holds.get(scene)?.release();
			await expectRows(scene);
		},
		async FAILS(scene) {
			await holds.get(scene)?.abort(500);
			await expect(scene.page.getByRole("button", { name: "Retry" })).toBeVisible();
		},
		async RETRY(scene) {
			await holds.get(scene)?.release();
			await scene.page.getByRole("button", { name: "Retry" }).click();
			await expectRows(scene);
		},
		async SEARCH(scene) {
			await scene.page.getByRole("searchbox", { name: "Search all files" }).fill("Quarter");
			await expect(scene.page.getByRole("link", { name: /^Search results for/ })).toBeVisible();
			await expectRows(scene);
		},
		async SEARCH_MISS(scene) {
			await scene.page.getByRole("searchbox", { name: "Search all files" }).fill("zxqv");
			await expect(scene.page.getByText("No files match this search")).toBeVisible();
		},
		async CLEAR_SEARCH(scene) {
			await scene.page.getByRole("button", { name: "Clear search" }).click();
			await expectRows(scene);
		},
		async FILTER(scene) {
			await typeFilter(scene).click();
			await scene.page.getByRole("option", { name: "Images" }).click();
			await scene.page.keyboard.press("Escape");
			await expectRows(scene);
		},
		async FILTER_MISS(scene) {
			await typeFilter(scene).click();
			await scene.page.getByRole("option", { name: "Videos" }).click();
			await scene.page.keyboard.press("Escape");
			await expect(scene.page.getByText("No videos here")).toBeVisible();
		},
		async CLEAR_FILTER(scene) {
			const clearFilter = scene.page.getByRole("button", { name: "Clear filter" });
			if (await clearFilter.isVisible()) await clearFilter.click();
			else {
				await typeFilter(scene).click();
				await scene.page.getByRole("button", { name: "Clear", exact: true }).click();
				await scene.page.keyboard.press("Escape");
			}
			await expectRows(scene);
		},
		async RESORT(scene) {
			holds.set(scene, await scene.hold(childrenOf(scene)));
			await scene.page.getByRole("button", { name: "Modified" }).click();
		},
		async SETTLES(scene) {
			await holds.get(scene)?.release();
			await expectRows(scene);
		},
		async OPEN_EMPTY(scene) {
			const empty = content.get(scene)?.emptyFolder;
			if (!empty) throw new Error("listing: the scene has no content");
			await row(scene.page, empty.name).click();
			await expect(scene.page.getByText("This folder is empty")).toBeVisible();
		},
	},
});
