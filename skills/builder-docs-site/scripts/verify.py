"""Check the built site in Chromium: live pages (light, dark, mobile) and the Builder editor canvas.

    python verify.py SPEC.json                                   # live checks, screenshots in ./shots
    python verify.py SPEC.json --routes /docs/a /docs/b/c        # specific routes
    python verify.py SPEC.json --editor "$(python cloud.py login-url --server S --site SITE)"

Exits 1 when a doc page has no h1, a page logs a console error, or the editor fails to load.
Look at the screenshots: the checks cannot see a wrong colour or a broken layout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

SHOTS = Path("shots")
DOC_CHECKS = """() => {
	const q = (s) => document.querySelectorAll(s).length;
	const text = (s) => document.querySelector(s)?.textContent.replace(/\\u200b/g, '').trim() || null;
	return {
		title: document.title,
		h1: text('.docs-content h1'),
		outline: q('.docs-outline-link'),
		active: text('a[data-sidebar-link].active'),
		pager: q('nav[aria-label="Pager"] a'),
		code: q('.docs-content div[class*="language-"]'),
		highlighted: q('.docs-content .vp-code span[style*="--shiki-light"]'),
		diagrams: q('.docs-content figure[data-diagram]'),
		drawn: q('.docs-content .diagram-canvas svg'),
	};
}"""


def chromium(playwright):
	executable = os.environ.get("CHROMIUM")
	if not executable:
		cached = sorted(Path.home().glob(".cache/ms-playwright/chromium-*/chrome-linux*/chrome"))
		executable = str(cached[-1]) if cached else None
	return playwright.chromium.launch(executable_path=executable) if executable else playwright.chromium.launch()


def deepest_link(groups: list) -> str | None:
	best = None
	for item in groups:
		found = deepest_link(item["items"]) if "items" in item else item.get("link")
		if found and (not best or found.count("/") > best.count("/")):
			best = found
	return best


def site_route(spec: dict, link: str) -> str:
	prefix, docs_dir = spec.get("route_prefix", "docs"), spec.get("docs_dir", "docs")
	path = link.split("#")[0].strip("/")
	for start in (prefix, docs_dir):
		if start and (path == start or path.startswith(start + "/")):
			path = path[len(start) + 1 :]
			break
	return f"/{prefix}/{path}" if path else "/"


def default_routes(spec: dict) -> list[str]:
	prefix = spec.get("route_prefix", "docs")
	routes = ["/", site_route(spec, spec.get("preview_route", f"/{prefix}"))]
	for sidebar in spec.get("sidebars", []):
		link = deepest_link(sidebar["groups"])
		if link and not link.startswith("/api/"):
			routes.append(site_route(spec, link))
	routes.append(f"/{prefix}/this-page-does-not-exist")
	routes += [f"/api-reference/{entry['name']}" for entry in spec.get("api_references", [])[:1]]
	return list(dict.fromkeys(routes))


def check_page(context, base: str, route: str, name: str, dark: bool = False, drawer: bool = False) -> dict:
	page = context.new_page()
	errors: list[str] = []
	page.on("console", lambda message: errors.append(message.text[:200]) if message.type == "error" else None)
	page.on("pageerror", lambda error: errors.append(str(error)[:200]))
	page.goto(base + route, wait_until="networkidle")
	if dark:
		page.click("[data-appearance]")
	if drawer:
		page.click("[data-menu-toggle]")
	page.wait_for_timeout(3000 if route.startswith("/api-reference/") else 2000)
	result = {"route": route, "errors": errors}
	if route.startswith("/api-reference/"):
		result["rendered"] = page.evaluate("() => document.querySelectorAll('[data-openapi-url] *').length > 50")
	elif route != "/":
		result.update(page.evaluate(DOC_CHECKS))
	if drawer:
		result["drawer"] = page.evaluate("() => getComputedStyle(document.querySelector('.docs-sidebar')).display")
	page.screenshot(path=str(SHOTS / f"{name}.png"))
	page.close()
	return result


def failed(result: dict) -> bool:
	route = result["route"]
	if result["errors"]:
		return True
	if route.startswith("/api-reference/"):
		return not result.get("rendered")
	return route != "/" and not result.get("h1")


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("spec")
	parser.add_argument("--routes", nargs="*")
	parser.add_argument("--editor", help="a one-time login URL from cloud.py login-url")
	parser.add_argument("--editor-route", help="the page to open in the editor (default: the 2-segment shell)")
	args = parser.parse_args()
	spec = json.loads(Path(args.spec).read_text())
	base = spec["site"].rstrip("/")
	SHOTS.mkdir(exist_ok=True)
	failures = 0
	with sync_playwright() as playwright:
		browser = chromium(playwright)
		desktop = browser.new_context(viewport={"width": 1440, "height": 900})
		routes = args.routes or default_routes(spec)
		for route in routes:
			result = check_page(desktop, base, route, route.strip("/").replace("/", "_") or "home")
			failures += failed(result)
			print(json.dumps(result))
		doc_route = next((route for route in routes if route.count("/") >= 2 and not route.startswith("/api-reference/")), routes[0])
		print(json.dumps(check_page(desktop, base, doc_route, "dark", dark=True)))
		mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
		print(json.dumps(check_page(mobile, base, doc_route, "mobile-drawer", drawer=True)))
		if args.editor:
			editor = browser.new_context(viewport={"width": 1600, "height": 1000})
			page = editor.new_page()
			errors: list[str] = []
			page.on("console", lambda message: errors.append(message.text[:200]) if message.type == "error" else None)
			page.goto(args.editor, wait_until="networkidle")
			route = args.editor_route or f"{spec.get('route_prefix', 'docs')}/:p1/:p2"
			query = urllib.parse.urlencode({"filters": json.dumps([["route", "=", route]]), "fields": json.dumps(["name"])})
			found = page.request.get(f"{base}/api/resource/Builder%20Page?{query}").json().get("data") or []
			if not found:
				sys.exit(f"no Builder Page with route {route}")
			page.goto(f"{base}/builder/page/{found[0]['name']}", wait_until="networkidle")
			page.wait_for_timeout(8000)
			page.screenshot(path=str(SHOTS / "editor.png"))
			failures += bool(errors)
			print(json.dumps({"editor": route, "errors": errors[:5]}))
		browser.close()
	print(f"screenshots in {SHOTS.resolve()}; {failures} failing checks")
	sys.exit(1 if failures else 0)


if __name__ == "__main__":
	main()
