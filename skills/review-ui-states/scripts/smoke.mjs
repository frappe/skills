// Serves a built canvas, walks a few arrow keys in the lightbox and screenshots the result.
// Run from the repo's Playwright folder so `@playwright/test` resolves:
//   node <skill>/scripts/smoke.mjs <build dir> <flow> <state> [ArrowRight ArrowDown ...]
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { resolve } from "node:path";

// Resolve @playwright/test from where the command runs, so the script can live outside the repo.
const { chromium } = createRequire(resolve(process.cwd(), "smoke.js"))("@playwright/test");

const [dir, flow, state, ...keys] = process.argv.slice(2);
if (!dir || !flow || !state) { console.error("usage: smoke.mjs <build dir> <flow> <state> [keys…]"); process.exit(2); }
const seq = keys.length ? keys : ["ArrowRight", "ArrowDown", "ArrowLeft"];
const port = 8765 + Math.floor(Math.random() * 1000);
const server = spawn("python3", ["-m", "http.server", String(port), "-d", dir], { stdio: "ignore" });
await new Promise((r) => setTimeout(r, 800));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 2000, height: 1150 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
try {
  await page.goto(`http://127.0.0.1:${port}/canvas.html#${flow}`);
  await page.waitForTimeout(800);
  await page.click(`.card[data-flow="${flow}"][data-state="${state}"]`);
  await page.waitForTimeout(300);
  for (const key of seq) {
    await page.keyboard.press(key);
    await page.waitForTimeout(150);
    console.log(`${key} -> ${await page.textContent("#lb-crumbs")}`);
  }
  await page.screenshot({ path: resolve(dir, "..", "smoke-lightbox.png") });
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  await page.screenshot({ path: resolve(dir, "..", "smoke-canvas.png") });
  console.log(errors.length ? `errors:\n${errors.join("\n")}` : "no page errors");
} finally {
  await browser.close();
  server.kill();
}
