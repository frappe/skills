#!/usr/bin/env node
/**
 * Builds the review canvas: one HTML page over every flow manifest in the capture
 * out dir, with the screenshots copied beside it. Findings are read from
 * <out dir>/findings.json when present.
 *
 *   node <skill>/assets/harness/canvas/build.mjs <out dir> <build dir> <app name>
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const [outArg, buildArg, app] = process.argv.slice(2);
const [outDir, buildDir] = [outArg, buildArg].map((p) => p && resolve(p));
if (!outDir || !buildDir || !app) {
	console.error("usage: node build.mjs <out dir> <build dir> <app name>");
	process.exit(1);
}

/** Canvas order, as the capture run records it from flows/index.ts; flows not captured yet are skipped. */
const orderPath = join(outDir, "index.json");
const ORDER = existsSync(orderPath) ? JSON.parse(readFileSync(orderPath, "utf8")) : [];

const findingsPath = join(outDir, "findings.json");
const findings = existsSync(findingsPath) ? JSON.parse(readFileSync(findingsPath, "utf8")) : {};

const present = new Set(readdirSync(outDir).filter((name) => name.endsWith(".json") && name !== "index.json" && name !== "findings.json").map((name) => name.slice(0, -5)));
const flows = [...ORDER.filter((id) => present.has(id)), ...[...present].filter((id) => !ORDER.includes(id))].map((id) => {
	const manifest = JSON.parse(readFileSync(join(outDir, `${id}.json`), "utf8"));
	return { ...manifest, findings: findings[id] ?? [] };
});

mkdirSync(buildDir, { recursive: true });
const shots = [];
for (const flow of flows) {
	for (const state of flow.states) {
		if (!state.screenshot) continue;
		const target = join(buildDir, state.screenshot);
		mkdirSync(dirname(target), { recursive: true });
		copyFileSync(join(outDir, state.screenshot), target);
		shots.push(state.screenshot);
	}
}

const meta = {
	builtAt: new Date().toISOString(),
	commit: process.env.UI_STATES_COMMIT ?? "",
	branch: process.env.UI_STATES_BRANCH ?? "",
};
const data = JSON.stringify({ meta, flows }).replace(/<\//g, "<\\/");
const template = readFileSync(join(here, "template.html"), "utf8");
writeFileSync(join(buildDir, "canvas.html"), template.replace("__DATA__", data).replaceAll("__APP__", app));
writeFileSync(join(buildDir, "files.json"), JSON.stringify(shots.map((path) => ({ path })), null, "\t"));

const captured = flows.reduce((n, flow) => n + flow.states.filter((s) => s.screenshot).length, 0);
console.log(`${flows.length} flows, ${captured} screenshots -> ${join(buildDir, "canvas.html")}`);
