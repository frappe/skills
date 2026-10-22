"""Draft a build spec from a VitePress repository checkout.

    python spec_from_vitepress.py REPO_DIR --repository owner/name --branch main \
        --site https://docs.example.frappe.cloud [--published https://owner.github.io/name/] > spec.json

Evaluates .vitepress/config.* with Node (type stripping, a stub `vitepress` module), then reads
the home hero, brand colours and API references. Review the output: anything it cannot read is
left out, and the build falls back to defaults.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = r"""
const STUB = "data:text/javascript,export const defineConfig = (c) => c; export default {};";
export async function resolve(specifier, context, next) {
	if (specifier === "vitepress" || specifier.startsWith("vitepress/")) return { url: STUB, shortCircuit: true };
	try {
		return await next(specifier, context);
	} catch (error) {
		for (const extension of [".ts", ".mts", ".js", ".mjs"]) {
			try {
				return await next(specifier + extension, context);
			} catch {}
		}
		if (!specifier.startsWith(".") && !specifier.startsWith("node:") && !specifier.startsWith("/")) return { url: STUB, shortCircuit: true };
		throw error;
	}
}
// VitePress bundles the config with esbuild, which provides __dirname and __filename.
export async function load(url, context, next) {
	const result = await next(url, context);
	if (!url.startsWith("file:") || !result.source) return result;
	const source = String(result.source);
	const uses = /\b__(dirname|filename)\b/.test(source);
	const declares = /\b(const|let|var)\s+__(dirname|filename)\b/.test(source);
	if (!uses || declares) return result;
	const path = new URL(url).pathname;
	const prelude = `const __filename = ${JSON.stringify(path)}; const __dirname = ${JSON.stringify(path.slice(0, path.lastIndexOf("/")))};\n`;
	return { ...result, source: prelude + source };
}
"""

EVALUATE = r"""
import { register } from "node:module";
import { pathToFileURL } from "node:url";
register(pathToFileURL(process.argv[2]));
const config = (await import(pathToFileURL(process.argv[3]))).default;
const theme = config.themeConfig || {};
console.log(JSON.stringify({ title: config.title, description: config.description, rewrites: config.rewrites,
	logo: theme.logo, nav: theme.nav, sidebar: theme.sidebar, footer: theme.footer, socialLinks: theme.socialLinks }));
"""


def find_config(repo: Path) -> tuple[Path, Path]:
	"""The VitePress root (where .vitepress lives) and its config file."""
	for root in (repo, repo / "docs"):
		for name in ("config.mts", "config.ts", "config.mjs", "config.js"):
			if (root / ".vitepress" / name).exists():
				return root, root / ".vitepress" / name
	sys.exit("no .vitepress/config.* in the repository root or docs/")


def evaluate(config: Path) -> dict:
	with tempfile.TemporaryDirectory() as temp:
		hooks, runner = Path(temp) / "hooks.mjs", Path(temp) / "evaluate.mjs"
		hooks.write_text(HOOKS)
		runner.write_text(EVALUATE)
		result = subprocess.run(["node", str(runner), str(hooks), str(config)], capture_output=True, text=True, cwd=config.parent)
	if result.returncode:
		sys.exit(f"could not evaluate {config}:\n{result.stderr[-2000:]}")
	return json.loads(result.stdout.strip().splitlines()[-1])


def frontmatter(path: Path) -> dict:
	text = path.read_text() if path.exists() else ""
	match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
	if not match:
		return {}
	try:
		import yaml
	except ImportError:
		print("PyYAML missing: hero left out", file=sys.stderr)
		return {}
	return yaml.safe_load(match.group(1)) or {}


def brand(vitepress: Path) -> dict:
	css = "\n".join(path.read_text() for path in (vitepress / "theme").glob("**/*.css")) if (vitepress / "theme").exists() else ""
	light = dict(re.findall(r"--vp-c-brand-([12]):\s*([^;]+);", css.split(".dark", 1)[0]))
	dark_block = re.search(r"\.dark\s*\{([^}]*)\}", css)
	dark = dict(re.findall(r"--vp-c-brand-([12]):\s*([^;]+);", dark_block.group(1))) if dark_block else {}
	result = {"color": light.get("1"), "hover": light.get("2"), "dark": dark.get("1"), "dark_hover": dark.get("2")}
	return {key: value.strip() for key, value in result.items() if value}


def sidebars(sidebar) -> list[dict]:
	"""VitePress multi-sidebars to spec variants: identical trees share one variant."""
	if not sidebar:
		return []
	if isinstance(sidebar, list):
		return [{"variant": "main", "label": "Sidebar", "prefixes": ["/"], "groups": sidebar}]
	variants: list[dict] = []
	for prefix, groups in sidebar.items():
		groups = groups["items"] if isinstance(groups, dict) else groups
		same = next((variant for variant in variants if variant["groups"] == groups), None)
		if same:
			same["prefixes"].append(prefix)
			continue
		label = groups[0].get("text", "Sidebar") if groups else "Sidebar"
		variants.append({"variant": "main" if not variants else re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_"), "label": label, "prefixes": [prefix], "groups": groups})
	return variants


def nav(items) -> list[dict]:
	out = []
	for item in items or []:
		entry = {"text": item["text"]}
		if item.get("activeMatch"):
			entry["match"] = item["activeMatch"]
		if item.get("items"):
			entry["items"] = [{"text": child["text"], "link": child["link"]} for child in item["items"] if child.get("link")]
		else:
			entry["link"] = item.get("link", "/")
		out.append(entry)
	return out


def api_references(vitepress: Path, repo: Path, published: str | None) -> list[dict]:
	"""Best effort: objects shaped { name, title, specification, server } in the VitePress config files."""
	pattern = re.compile(r"\{\s*name:\s*'([^']+)',\s*title:\s*'([^']+)',\s*specification:\s*'([^']+)'(?:,\s*server:\s*'([^']+)')?\s*\}")
	found = []
	for path in vitepress.glob("*.*ts"):
		for name, title, specification, server in pattern.findall(path.read_text()):
			spec = specification
			if not (repo / specification).exists():
				if not published:
					print(f"{title}: {specification} is generated at build time; pass --published to use the deployed copy", file=sys.stderr)
					continue
				spec = published.rstrip("/") + f"/api/{name}/openapi.json"
			found.append({"name": name, "title": title, "spec": spec, "server": server})
	return found


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("repo", type=Path)
	parser.add_argument("--repository", required=True)
	parser.add_argument("--branch", default="main")
	parser.add_argument("--site", required=True)
	parser.add_argument("--published", help="the deployed VitePress site, for build-time generated files")
	args = parser.parse_args()
	repo = args.repo.resolve()
	root, config_path = find_config(repo)
	config = evaluate(config_path)
	vitepress = config_path.parent
	docs_dir = str(root.relative_to(repo)) if root != repo else ""
	rewrites = config.get("rewrites") or {}
	home_source = next((source for source, target in rewrites.items() if target == "index.md"), "index.md")
	if not docs_dir and "/" in home_source:
		docs_dir = home_source.split("/")[0]
	home_path = (root / home_source) if root != repo else (repo / home_source)
	logo = config.get("logo")
	logo = logo.get("src") if isinstance(logo, dict) else logo
	if logo and logo.startswith("/"):
		logo = str((vitepress / "public" / logo.lstrip("/")).relative_to(repo))
	hero = (frontmatter(home_path).get("hero") or {})
	spec = {
		"site": args.site,
		"repository": args.repository,
		"branch": args.branch,
		"title": config.get("title") or args.repository.split("/")[-1],
		"description": config.get("description", ""),
		"logo": logo or "",
		"docs_dir": docs_dir,
		"route_prefix": "docs",
		"home": {"source": str(home_path.relative_to(repo)), "hero": hero},
		"brand": brand(vitepress),
		"nav": nav(config.get("nav")),
		"sidebars": sidebars(config.get("sidebar")),
		"source_links": {"directories": []},
		"api_references": api_references(vitepress, repo, args.published),
		"footer": config.get("footer") or {},
		"github_link": next((link["link"] for link in config.get("socialLinks") or [] if link.get("icon") == "github"), f"https://github.com/{args.repository}"),
	}
	if spec["sidebars"]:
		first = spec["sidebars"][0]["groups"][0]
		link = first.get("link") or (first.get("items") or [{}])[0].get("link")
		spec["preview_route"] = link or "/"
	print(json.dumps(spec, indent=1))


if __name__ == "__main__":
	main()
