import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { request, type FullConfig } from "@playwright/test";
import provisionUsers from "../drive-backed-apps/global-setup";
import { loginViaApi, type Credentials } from "../shared/auth";

/** Real-looking names, so screenshots read like a workspace and not a test run. */
const NAMES = [
	["Priya", "Nair"],
	["Arjun", "Mehta"],
	["Sana", "Iqbal"],
	["Rohan", "Desai"],
] as const;

/** Provisions the e2e users, then gives them names fit for a screenshot. */
export default async function globalSetup(config: FullConfig): Promise<void> {
	await provisionUsers(config);
	const baseURL = config.projects[0]?.use.baseURL as string;
	const statePath = resolve(__dirname, "../drive-backed-apps/.state/run.json");
	const { users } = JSON.parse(readFileSync(statePath, "utf8")) as { users: Credentials[] };
	const admin = await request.newContext({ baseURL });
	await loginViaApi(admin);
	for (const [index, user] of users.entries()) {
		const [first_name, last_name] = NAMES[index % NAMES.length];
		const response = await admin.put(`/api/resource/User/${encodeURIComponent(user.email)}`, {
			data: { first_name, last_name },
		});
		if (!response.ok()) throw new Error(`Renaming ${user.email} failed: ${response.status()}`);
	}
	await admin.dispose();
}
