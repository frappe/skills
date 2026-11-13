import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

/**
 * Example from a Frappe app's Drive module; adapt it to your app's e2e setup.
 * Captures every Drive UI state as a screenshot, walking the machines under
 * `flows/`. Not a test suite: one run per flow, no retries, one browser.
 *
 * Needs the same `suite.drive.e2e_api` server as `drive-backed-apps`: set
 * `BASE_URL`, `E2E_TEST_API_URL` (a `DEV_SERVER=1` frappe serve on another
 * port) and `E2E_BENCH_PATH` (the bench that serves the site).
 */
const baseURL = process.env.BASE_URL ?? "http://localhost:8000";
const testApiUrl = process.env.E2E_TEST_API_URL ?? baseURL.replace(/:\d+$/, ":8095");
process.env.E2E_TEST_API_URL = testApiUrl;
const benchPath = process.env.E2E_BENCH_PATH;
if (!benchPath) throw new Error("E2E_BENCH_PATH must name the bench that serves BASE_URL");

export const OUT_DIR = resolve(__dirname, "out");

export default defineConfig({
	testDir: __dirname,
	testMatch: /capture\.spec\.ts/,
	outputDir: resolve(__dirname, ".runs"),
	fullyParallel: true,
	retries: 0,
	// Two workers so global setup provisions four users: actor, peer, fresh, spare.
	workers: 2,
	timeout: 15 * 60_000,
	expect: { timeout: 10_000 },
	reporter: [["list"]],
	use: {
		baseURL,
		viewport: { width: 1440, height: 900 },
		actionTimeout: 15_000,
		navigationTimeout: 30_000,
		launchOptions: { args: ["--unsafely-treat-insecure-origin-as-secure=" + baseURL] },
	},
	projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
	webServer: {
		url: new URL("/api/method/suite.drive.e2e_api.provision_users", testApiUrl).href,
		command: `${resolve(benchPath, "env/bin/python")} -m frappe.utils.bench_helper frappe serve --port ${new URL(testApiUrl).port} --noreload`,
		cwd: resolve(benchPath, "sites"),
		env: { ...process.env, DEV_SERVER: "1" } as Record<string, string>,
		reuseExistingServer: true,
		timeout: 120_000,
		gracefulShutdown: { signal: "SIGTERM" as const, timeout: 5_000 },
	},
	globalSetup: "./global-setup.ts",
	globalTeardown: "../drive-backed-apps/global-teardown.ts",
});
