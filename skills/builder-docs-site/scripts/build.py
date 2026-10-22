"""Build a GitHub-backed docs site in Frappe Builder from a spec (see SKILL.md, examples/).

    python build.py SPEC.json                 # tokens, components, pages; lint-gated; idempotent
    python build.py SPEC.json --emit out/     # write the generated trees and scripts, push nothing
    python build.py SPEC.json --clean-routes  # also delete static pages under the docs prefix

Credentials: FRAPPE_API_KEY / FRAPPE_API_SECRET, or .cloudv2/<host>.json written by
`cloud.py site-key`. Lints with the frappe-builder skill's linter (found next to this skill or
downloaded once).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL / "templates"
CACHE = Path.home() / ".cache" / "builder-docs-site"
LINT_URL = "https://raw.githubusercontent.com/frappe/builder/master/skills/frappe-builder/scripts/lint.py"
FONT = "Inter"
NAV_HEIGHT = "64px"
SIDEBAR_WIDTH = "280px"
DOC_COMPONENT = "doc-page"
NAV_COMPONENT = "doc-navbar"
API_COMPONENT_PAGE = "api-reference/:name"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blocks import DEFINITIONS, block, body, compact_json, instance, normalize, prop, stabilize_ids, text  # noqa: E402

# ---------------------------------------------------------------- site API


class Site:
	def __init__(self, url: str):
		self.url = url.rstrip("/")
		key, secret = os.environ.get("FRAPPE_API_KEY"), os.environ.get("FRAPPE_API_SECRET")
		if not (key and secret):
			state = Path(".cloudv2") / f"{urllib.parse.urlparse(self.url).hostname}.json"
			if not state.exists():
				sys.exit(f"no credentials: set FRAPPE_API_KEY/FRAPPE_API_SECRET or run cloud.py site-key ({state})")
			saved = json.loads(state.read_text())
			key, secret = saved["api_key"], saved["api_secret"]
		self.auth = f"token {key}:{secret}"

	def call(self, method: str, path: str, payload=None, retries: int = 4):
		data = json.dumps(payload).encode() if payload is not None else None
		request = urllib.request.Request(self.url + path, data=data, method=method)
		request.add_header("Authorization", self.auth)
		request.add_header("Accept", "application/json")
		if data is not None:
			request.add_header("Content-Type", "application/json")
		for attempt in range(retries):
			try:
				with urllib.request.urlopen(request, timeout=90) as response:
					return json.loads(response.read() or b"{}")
			except urllib.error.HTTPError as error:
				detail = error.read().decode(errors="replace")
				if error.code == 404 and method == "GET":
					return None
				retriable = error.code >= 500 or "DocumentLockedError" in detail or "TimestampMismatchError" in detail
				if retriable and attempt < retries - 1:
					time.sleep(3 * (attempt + 1))
					continue
				raise SystemExit(f"{method} {path} -> {error.code}: {detail[:800]}") from None

	@staticmethod
	def resource(doctype: str, name: str = "") -> str:
		path = "/api/resource/" + urllib.parse.quote(doctype)
		return path + ("/" + urllib.parse.quote(name, safe="") if name else "")

	def names(self, doctype: str, filters=None, fields=("name",)) -> list[dict]:
		query = {"fields": json.dumps(list(fields)), "limit_page_length": 0}
		if filters:
			query["filters"] = json.dumps(filters)
		return self.call("GET", self.resource(doctype) + "?" + urllib.parse.urlencode(query))["data"]


# ---------------------------------------------------------------- lint (frappe-builder skill)


def load_linter():
	candidates = [
		os.environ.get("FRAPPE_BUILDER_SKILL", ""),
		str(SKILL.parent / "frappe-builder"),
		str(CACHE / "frappe-builder"),
	]
	for candidate in candidates:
		if candidate and (Path(candidate) / "scripts" / "lint.py").exists():
			sys.path.insert(0, str(Path(candidate) / "scripts"))
			import lint

			return lint.Linter
	target = CACHE / "frappe-builder" / "scripts"
	target.mkdir(parents=True, exist_ok=True)
	with urllib.request.urlopen(LINT_URL, timeout=60) as response:
		(target / "lint.py").write_bytes(response.read())
	sys.path.insert(0, str(target))
	import lint

	return lint.Linter


Linter = load_linter()
# Deliberate: the content containers are filled by bindings and scripts, not edited in place.
ACCEPTED = ("text and layout in raw HTML can't be edited in the editor",)


def lint(kind: str, name: str, roots: list[dict], tokens: set[str], components: set[str], data_script: str = "") -> None:
	issues = Linter(roots, tokens, components, kind, dict(DEFINITIONS), data_script).run()
	shown = [issue for issue in issues if not any(ok in issue[2] for ok in ACCEPTED)]
	for level, where, message in shown:
		print(f"  lint {kind} {name}: {level} {where}: {message}")
	if any(level == "error" for level, _, _ in shown):
		raise SystemExit(f"lint errors in {kind} {name}; nothing pushed for it")


# ---------------------------------------------------------------- spec helpers


class Spec:
	def __init__(self, data: dict):
		self.data = data
		self.repository = data["repository"]
		self.branch = data.get("branch", "main")
		self.title = data.get("title", self.repository.split("/")[-1])
		self.docs_dir = data.get("docs_dir", "docs").strip("/")
		self.prefix = data.get("route_prefix", "docs").strip("/")
		self.cdn = f"https://cdn.jsdelivr.net/gh/{self.repository}@{self.branch}/"
		self.github = f"https://github.com/{self.repository}/"
		logo = data.get("logo", "")
		self.logo = logo if logo.startswith("http") else (self.cdn + logo.lstrip("/") if logo else "")

	def route(self, link: str) -> str:
		"""A VitePress link to this site's route: docs_dir pages and other repo pages under /prefix."""
		if link.startswith("http"):
			return link
		if link.startswith("/api/"):
			return "/api-reference/" + link.strip("/").split("/")[1]
		path = link.split("#")[0].strip("/")
		fragment = "#" + link.split("#", 1)[1] if "#" in link else ""
		if path.startswith(self.prefix + "/") or path == self.prefix:
			path = path[len(self.prefix) + 1 :]
		elif self.docs_dir and (path.startswith(self.docs_dir + "/") or path == self.docs_dir):
			path = path[len(self.docs_dir) + 1 :]
		return (f"/{self.prefix}/{path}" if path else "/") + fragment


def default_tokens(brand: dict) -> list[tuple[str, str, str, str]]:
	"""VitePress default palette; brand colours come from the spec."""
	color, dark = brand.get("color", "#3451b2"), brand.get("dark", "#a8b1ff")
	return [
		("bg", "Background", "#ffffff", "#1b1b1f"),
		("bg-alt", "Background alt", "#f6f6f7", "#161618"),
		("bg-soft", "Background soft", "#f6f6f7", "#202127"),
		("bg-elv", "Background elevated", "#ffffff", "#202127"),
		("text-1", "Text", "#3c3c43", "#dfdfd6"),
		("text-2", "Text muted", "#67676c", "#98989f"),
		("text-3", "Text subtle", "#929295", "#6a6a71"),
		("divider", "Divider", "#e2e2e3", "#2e2e32"),
		("gutter", "Gutter", "#e2e2e3", "#000000"),
		("border", "Border", "#c2c2c4", "#3c3f44"),
		("brand", "Brand", color, dark),
		("brand-2", "Brand hover", brand.get("hover", color), brand.get("dark_hover", dark)),
		("brand-soft", "Brand soft", brand.get("soft", "rgba(100, 108, 255, 0.14)"), brand.get("dark_soft", "rgba(100, 108, 255, 0.16)")),
		("soft", "Soft fill", "rgba(142, 150, 170, 0.14)", "rgba(101, 117, 133, 0.16)"),
		("tip-soft", "Tip fill", "rgba(100, 108, 255, 0.14)", "rgba(100, 108, 255, 0.16)"),
		("warning-soft", "Warning fill", "rgba(234, 179, 8, 0.14)", "rgba(234, 179, 8, 0.16)"),
		("danger-soft", "Danger fill", "rgba(244, 63, 94, 0.14)", "rgba(244, 63, 94, 0.16)"),
		("code-bg", "Inline code fill", "rgba(142, 150, 170, 0.14)", "rgba(101, 117, 133, 0.16)"),
		("code-color", "Inline code text", "#3451b2", "#a8b1ff"),
		("code-block-bg", "Code block fill", "#f6f6f7", "#161618"),
		("backdrop", "Backdrop", "rgba(0, 0, 0, 0.6)", "rgba(0, 0, 0, 0.6)"),
		("knob", "Switch knob", "#ffffff", "#000000"),
	]


def var(name: str) -> str:
	return f"var(--token-{name})"


# ---------------------------------------------------------------- blocks

ICONS = {
	"search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
	"chevron-down": '<path d="m6 9 6 6 6-6"/>',
	"chevron-right": '<path d="m9 6 6 6-6 6"/>',
	"sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
	"moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
	"menu": '<path d="M4 6h16M4 12h10M4 18h16"/>',
}
GITHUB_SVG = (
	'<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.4-1.8-1.4-1.8-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.7-.3-5.5-1.3-5.5-6 0-1.2.5-2.3 1.2-3.1-.1-.4-.5-1.6.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.7 18.3 5 18.3 5c.7 1.6.2 2.8.1 3.2.8.8 1.2 1.9 1.2 3.1 0 4.6-2.8 5.6-5.5 5.9.5.4.9 1.1.9 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3"/></svg>'
)


def icon(name: str, label: str, size: str, color: str | None = None) -> dict:
	markup = f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
	style = {"display": "flex", "alignItems": "center", "justifyContent": "center", "width": size, "height": size, "flexShrink": "0"}
	if color:
		style["color"] = color
	return block("div", style, name=label, text=markup, raw_html=True, classes=[f"docs-icon-{name}"])


def nav_link_style() -> dict:
	return {"fontFamily": FONT, "fontSize": "14px", "fontWeight": "500", "lineHeight": NAV_HEIGHT, "padding": "0 12px", "color": var("text-1"), "textDecoration": "none", "whiteSpace": "nowrap", "hover:color": var("brand")}


def navbar(spec: Spec) -> dict:
	menu = []
	for item in spec.data.get("nav", []):
		match = item.get("match") or "^" + spec.route(item.get("link", "/")).rstrip("/")
		if "items" not in item:
			menu.append(text("a", item["text"], nav_link_style(), name=item["text"], attrs={"href": spec.route(item["link"]), "data-active-match": match}, classes=["docs-nav-link"]))
			continue
		flyout = [
			text("a", child["text"], {"display": "block", "padding": "0 12px", "borderRadius": "6px", "fontFamily": FONT, "fontSize": "14px", "fontWeight": "500", "lineHeight": "32px", "color": var("text-1"), "textDecoration": "none", "whiteSpace": "nowrap", "hover:color": var("brand"), "hover:backgroundColor": var("soft")}, name=child["text"], attrs={"href": spec.route(child["link"])})
			for child in item["items"]
		]
		menu.append(
			block(
				"div",
				{"position": "relative", "display": "flex", "alignItems": "center"},
				[
					block("button", {**nav_link_style(), "display": "flex", "alignItems": "center", "gap": "4px", "border": "none", "backgroundColor": "transparent", "cursor": "pointer"}, [text("span", item["text"], {"fontFamily": FONT, "fontSize": "14px", "fontWeight": "500"}, name="Label"), icon("chevron-down", "Caret", "14px")], name="Button", attrs={"type": "button", "aria-haspopup": "true", "aria-expanded": "false"}, classes=["docs-nav-link"]),
					block("div", {"position": "absolute", "top": "52px", "right": "0", "minWidth": "180px", "padding": "12px", "display": "flex", "flexDirection": "column", "borderRadius": "12px", "borderWidth": "1px", "borderStyle": "solid", "borderColor": var("divider"), "backgroundColor": var("bg-elv"), "boxShadow": "0 12px 32px rgba(0, 0, 0, 0.1), 0 2px 6px rgba(0, 0, 0, 0.08)", "zIndex": "40"}, flyout, name="Flyout", classes=["docs-flyout"]),
				],
				name=item["text"],
				attrs={"data-flyout": "", "data-active-match": match},
				classes=["docs-nav-group"],
			)
		)
	github = spec.data.get("github_link", spec.github.rstrip("/"))
	return block(
		"header",
		{"width": "100%", "height": NAV_HEIGHT, "display": "flex", "alignItems": "center", "gap": "16px", "padding": "0 32px", "boxSizing": "border-box", "backgroundColor": var("bg"), "borderBottomWidth": "1px", "borderBottomStyle": "solid", "borderBottomColor": var("gutter")},
		[
			block(
				"a",
				{"display": "flex", "alignItems": "center", "gap": "8px", "height": NAV_HEIGHT, "minWidth": "216px", "flexShrink": "0", "textDecoration": "none"},
				([block("img", {"width": "24px", "height": "24px"}, name="Logo", attrs={"src": spec.logo, "alt": ""})] if spec.logo else [])
				+ [text("span", spec.title, {"fontFamily": FONT, "fontSize": "16px", "fontWeight": "600", "color": var("text-1")}, name="Title")],
				name="Home link",
				attrs={"href": "/"},
				tablet={"minWidth": "0"},
			),
			block(
				"button",
				{"display": "flex", "alignItems": "center", "gap": "8px", "height": "40px", "minWidth": "176px", "padding": "0 10px 0 12px", "borderRadius": "8px", "borderWidth": "1px", "borderStyle": "solid", "borderColor": "transparent", "backgroundColor": var("bg-alt"), "color": var("text-2"), "cursor": "pointer", "hover:borderColor": var("brand")},
				[
					icon("search", "Search icon", "14px"),
					text("span", "Search", {"flexGrow": "1", "textAlign": "left", "fontFamily": FONT, "fontSize": "13px", "fontWeight": "500", "color": var("text-2")}, name="Search label", mobile={"display": "none"}),
					text("span", "Ctrl K", {"padding": "0 6px", "borderRadius": "4px", "borderWidth": "1px", "borderStyle": "solid", "borderColor": var("divider"), "fontFamily": FONT, "fontSize": "12px", "fontWeight": "500", "lineHeight": "22px", "color": var("text-3")}, name="Shortcut", mobile={"display": "none"}),
				],
				name="Search",
				attrs={"type": "button", "aria-label": "Search", "data-search-open": ""},
				mobile={"minWidth": "0", "backgroundColor": "transparent"},
			),
			block("div", {"flexGrow": "1"}, name="Spacer"),
			block("nav", {"display": "flex", "alignItems": "center"}, menu, name="Menu", attrs={"aria-label": "Main"}, tablet={"display": "none"}),
			block("div", {"width": "1px", "height": "24px", "margin": "0 8px", "backgroundColor": var("divider")}, name="Divider", tablet={"display": "none"}),
			block(
				"button",
				{"position": "relative", "width": "40px", "height": "22px", "flexShrink": "0", "padding": "0", "borderRadius": "11px", "borderWidth": "1px", "borderStyle": "solid", "borderColor": var("border"), "backgroundColor": var("soft"), "cursor": "pointer", "hover:borderColor": var("brand")},
				[block("span", {"position": "absolute", "top": "1px", "left": "1px", "width": "18px", "height": "18px", "display": "flex", "alignItems": "center", "justifyContent": "center", "borderRadius": "50%", "backgroundColor": var("knob"), "color": var("text-2")}, [icon("sun", "Sun", "12px"), icon("moon", "Moon", "12px")], name="Knob", classes=["docs-knob"])],
				name="Appearance",
				attrs={"type": "button", "role": "switch", "aria-checked": "false", "aria-label": "Toggle dark mode", "title": "Toggle dark mode", "data-appearance": ""},
				classes=["docs-appearance"],
				mobile={"display": "none"},
			),
			block("a", {"display": "flex", "alignItems": "center", "justifyContent": "center", "width": "36px", "height": "36px", "flexShrink": "0", "color": var("text-2"), "hover:color": var("text-1")}, [block("div", {"display": "flex", "alignItems": "center"}, name="GitHub icon", text=GITHUB_SVG, raw_html=True)], name="GitHub", attrs={"href": github, "target": "_blank", "rel": "noopener", "aria-label": "GitHub"}, mobile={"display": "none"}),
			block("button", {"display": "none", "alignItems": "center", "justifyContent": "center", "width": "40px", "height": "40px", "padding": "0", "border": "none", "backgroundColor": "transparent", "color": var("text-1"), "cursor": "pointer"}, [icon("menu", "Menu icon", "20px")], name="Menu button", attrs={"type": "button", "aria-label": "Open the sidebar", "data-menu-toggle": ""}, tablet={"display": "flex"}),
		],
		name="Doc Navbar",
		props={
			"repository": prop("string", spec.repository, label="GitHub repository"),
			"branch": prop("string", spec.branch, label="Branch"),
			"docs_dir": prop("string", spec.docs_dir, label="Docs folder in the repository"),
			"route_prefix": prop("string", spec.prefix, label="Route prefix"),
		},
		js=(TEMPLATES / "navbar.js").read_text(),
		css=(TEMPLATES / "navbar.css").read_text(),
	)


def sidebar_item(spec: Spec, item: dict, level: int) -> dict:
	if "items" in item:
		collapsible = item.get("collapsed") is not None
		heading = [text("h2" if level == 0 else "h3", item["text"], {"margin": "0", "fontFamily": FONT, "fontSize": "14px", "lineHeight": "24px", "fontWeight": "700" if level == 0 else "500", "color": var("text-1") if level == 0 else var("text-2")}, name="Title")]
		heading_attrs = {}
		if collapsible:
			caret = icon("chevron-right", "Caret", "14px", var("text-3"))
			caret["classes"].append("docs-sb-caret")
			heading.append(caret)
			heading_attrs = {"data-sidebar-toggle": "", "role": "button", "tabindex": "0"}
		return block(
			"section",
			{"display": "flex", "flexDirection": "column", **({"paddingBottom": "20px"} if level == 0 else {})},
			[
				block("div", {"display": "flex", "alignItems": "center", "justifyContent": "space-between", "gap": "8px", "padding": "4px 0", "cursor": "pointer" if collapsible else "default"}, heading, name="Heading", attrs=heading_attrs, classes=["docs-sb-heading"]),
				block("div", {"display": "flex", "flexDirection": "column", **({"paddingLeft": "16px", "borderLeftWidth": "1px", "borderLeftStyle": "solid", "borderLeftColor": var("divider")} if level > 0 else {})}, [sidebar_item(spec, child, level + 1) for child in item["items"]], name="Items", classes=["docs-sb-items"]),
			],
			name=item["text"],
			attrs={"data-sidebar-group": ""},
			classes=["docs-sb-group", f"level-{level}"] + (["collapsed"] if item.get("collapsed") else []),
		)
	attrs = {"href": spec.route(item["link"]), "data-sidebar-link": ""}
	if item.get("target"):
		attrs.update({"target": item["target"], "rel": "noopener"})
	return text("a", item["text"], {"display": "block", "padding": "4px 0", "fontFamily": FONT, "fontSize": "14px", "lineHeight": "24px", "fontWeight": "500", "color": var("text-2"), "textDecoration": "none", "hover:color": var("text-1")}, name=item["text"], attrs=attrs, classes=["docs-sb-link"])


def sidebar(spec: Spec) -> dict:
	"""One column holding every navigation: the canvas dims hidden blocks instead of removing them."""
	navigations = [
		block("nav", {"display": "flex", "flexDirection": "column"}, [sidebar_item(spec, group, 0) for group in entry["groups"]], name=f"{entry['variant']} navigation", attrs={"aria-label": entry.get("label", entry["variant"]), "data-sidebar-variant": entry["variant"]}, visible_if=f"component.show_{entry['variant']}")
		for entry in spec.data.get("sidebars", [])
	]
	return block(
		"aside",
		{"position": "sticky", "top": NAV_HEIGHT, "alignSelf": "flex-start", "width": SIDEBAR_WIDTH, "height": f"calc(100vh - {NAV_HEIGHT})", "flexShrink": "0", "padding": "24px 32px 96px", "boxSizing": "border-box", "overflowY": "auto", "backgroundColor": var("bg-alt")},
		navigations,
		name="Sidebar",
		classes=["docs-sidebar"],
		tablet={"display": "none"},
	)


def pager_link(side: str) -> dict:
	label = "Previous page" if side == "prev" else "Next page"
	return block(
		"a",
		{"display": "flex", "flexDirection": "column", "alignItems": "flex-start" if side == "prev" else "flex-end", "padding": "11px 16px 13px", "borderRadius": "8px", "borderWidth": "1px", "borderStyle": "solid", "borderColor": var("divider"), "textDecoration": "none", "gridColumn": "1" if side == "prev" else "2", "hover:borderColor": var("brand")},
		[
			text("span", label, {"fontFamily": FONT, "fontSize": "12px", "fontWeight": "500", "lineHeight": "20px", "color": var("text-2")}, name="Label"),
			text("span", label, {"fontFamily": FONT, "fontSize": "14px", "fontWeight": "500", "lineHeight": "20px", "color": var("brand")}, name="Title", bind={"innerHTML": f"component.{side}_title"}),
		],
		name="Previous" if side == "prev" else "Next",
		attrs={"href": "#"},
		bind={"href": f"component.{side}_href"},
		visible_if=f"component.has_{side}",
		mobile={"gridColumn": "1"},
	)


def doc_page(spec: Spec) -> dict:
	# A text element, so the editor canvas shows the bound HTML; published pages render p as div.
	content = block("p", {"width": "100%", "margin": "0"}, name="Content", text="The page renders from its Markdown on GitHub.", bind={"innerHTML": "component.content_html"}, classes=["docs-content"])
	footer = block(
		"footer",
		{"display": "flex", "flexDirection": "column", "gap": "24px", "marginTop": "64px"},
		[
			block("div", {"display": "flex", "justifyContent": "flex-end"}, [text("a", "View this page on GitHub", {"fontFamily": FONT, "fontSize": "14px", "fontWeight": "500", "color": var("brand"), "textDecoration": "none", "hover:color": var("brand-2")}, name="Source link", attrs={"href": spec.github, "target": "_blank", "rel": "noopener"}, bind={"href": "component.source_url"})], name="Edit row"),
			block("nav", {"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "paddingTop": "24px", "borderTopWidth": "1px", "borderTopStyle": "solid", "borderTopColor": var("divider")}, [pager_link("prev"), pager_link("next")], name="Pager", attrs={"aria-label": "Pager"}, visible_if="component.has_pager", mobile={"gridTemplateColumns": "1fr"}),
		],
		name="Doc footer",
		visible_if="component.source_url",
	)
	outline = block(
		"aside",
		{"position": "sticky", "top": "96px", "alignSelf": "flex-start", "width": "224px", "flexShrink": "0", "maxHeight": "calc(100vh - 128px)", "overflowY": "auto"},
		[
			text("p", "On this page", {"margin": "0", "fontFamily": FONT, "fontSize": "14px", "fontWeight": "600", "lineHeight": "32px", "color": var("text-1")}, name="Title"),
			block(
				"ul",
				{"margin": "0", "padding": "0 0 0 12px", "listStyle": "none", "borderLeftWidth": "1px", "borderLeftStyle": "solid", "borderLeftColor": var("divider")},
				[block("li", {"display": "block"}, [text("a", "Section", {"display": "block", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap", "fontFamily": FONT, "fontSize": "14px", "lineHeight": "32px", "color": var("text-2"), "textDecoration": "none", "hover:color": var("text-1")}, name="Link", attrs={"href": "#"}, bind={"innerHTML": "component.text", "href": "component.href"}, classes=["docs-outline-link"])], name="Item")],
				name="Links",
				repeat="component.outline",
			),
		],
		name="Outline",
		visible_if="component.has_outline",
		classes=["docs-outline"],
		tablet={"display": "none"},
	)
	main = block(
		"main",
		{"display": "flex", "justifyContent": "center", "gap": "32px", "flexGrow": "1", "minWidth": "0", "padding": "32px 48px 96px", "boxSizing": "border-box"},
		[block("article", {"flexGrow": "1", "minWidth": "0", "maxWidth": "760px"}, [content, footer], name="Article"), outline],
		name="Main",
		tablet={"padding": "32px 32px 80px"},
		mobile={"padding": "24px 24px 64px"},
	)
	return block(
		"div",
		{"display": "flex", "alignItems": "stretch", "width": "100%", "minHeight": f"calc(100vh - {NAV_HEIGHT})", "backgroundColor": var("bg")},
		[sidebar(spec), main, block("div", {"display": "none", "position": "fixed", "inset": "0", "zIndex": "50", "backgroundColor": var("backdrop")}, name="Backdrop", classes=["docs-sidebar-backdrop"])],
		name="Doc Page",
		props={"preview_route": prop("string", spec.data.get("preview_route", f"/{spec.prefix}"), label="Editor preview route")},
		js=(TEMPLATES / "doc_page.js").read_text(),
		css=(TEMPLATES / "doc_page.css").read_text(),
	)


def page_body(children: list) -> dict:
	return body(children, {"alignItems": "stretch", "flexWrap": "nowrap", "backgroundColor": var("bg"), "minHeight": "100vh"})


def sticky_navbar() -> dict:
	return instance(NAV_COMPONENT, style={"position": "sticky", "top": "0", "zIndex": "30"})


def home_page(spec: Spec) -> dict:
	home = spec.data.get("home", {})
	hero = home.get("hero") or {"name": spec.title, "text": "", "tagline": "", "actions": []}
	big = {"margin": "0", "fontFamily": FONT, "fontSize": "56px", "lineHeight": "64px", "fontWeight": "700", "letterSpacing": "-0.035em"}
	small = {"fontSize": "32px", "lineHeight": "40px"}
	actions = [
		text("a", action["text"], {"display": "inline-block", "padding": "0 20px", "borderRadius": "20px", "fontFamily": FONT, "fontSize": "14px", "fontWeight": "600", "lineHeight": "40px", "textDecoration": "none", **({"color": "#ffffff", "backgroundColor": var("brand"), "hover:backgroundColor": var("brand-2")} if action.get("theme", "brand") == "brand" else {"color": var("text-1"), "backgroundColor": var("soft")})}, name=action["text"], attrs={"href": spec.route(action["link"])})
		for action in hero.get("actions", [])
	]
	hero_children = [text("h1", hero.get("name", spec.title), {**big, "color": var("brand")}, name="Name", mobile=small)]
	if hero.get("text"):
		hero_children.append(text("p", hero["text"], {**big, "color": var("text-1")}, name="Headline", mobile=small))
	if hero.get("tagline"):
		hero_children.append(text("p", hero["tagline"], {"margin": "16px 0 0", "maxWidth": "620px", "fontFamily": FONT, "fontSize": "19px", "lineHeight": "1.55", "fontWeight": "500", "color": var("text-2")}, name="Tagline", mobile={"fontSize": "16px"}))
	if actions:
		hero_children.append(block("div", {"display": "flex", "gap": "12px", "paddingTop": "32px"}, actions, name="Actions"))
	image = (hero.get("image") or {}).get("src")
	hero_row = [block("div", {"display": "flex", "flexDirection": "column", "maxWidth": "650px"}, hero_children, name="Hero text")]
	if image or spec.logo:
		src = spec.logo if not image or image.startswith("/") and spec.logo else image
		hero_row.append(block("div", {"display": "flex", "alignItems": "center", "justifyContent": "center", "width": "220px", "height": "220px", "flexShrink": "0"}, [block("img", {"width": "180px", "maxWidth": "180px"}, name="Logo", attrs={"src": src, "alt": (hero.get("image") or {}).get("alt", spec.title)})], name="Hero image", tablet={"width": "160px", "height": "160px"}, mobile={"display": "none"}))
	line = {"margin": "0", "fontFamily": FONT, "fontSize": "14px", "fontWeight": "500", "lineHeight": "24px", "color": var("text-2")}
	footer = spec.data.get("footer", {})
	css = (TEMPLATES / "home.css").read_text() + "\n" + home.get("css", "")
	return page_body(
		[
			sticky_navbar(),
			block("section", {"display": "flex", "alignItems": "center", "justifyContent": "space-between", "gap": "48px", "width": "100%", "maxWidth": "1080px", "margin": "0 auto", "padding": "80px 48px 32px", "boxSizing": "border-box"}, hero_row, name="Hero", mobile={"padding": "48px 24px 24px"}),
			block("main", {"width": "100%", "maxWidth": "1080px", "margin": "0 auto", "padding": "0 48px 80px", "boxSizing": "border-box"}, [block("p", {"width": "100%", "margin": "0"}, name="Home content", text="The home body renders from its Markdown on GitHub.", bind={"innerHTML": "data.home_html"}, classes=["docs-home-content"], css=css)], name="Body", mobile={"padding": "0 24px 48px"}),
			block("footer", {"width": "100%", "padding": "32px 24px", "boxSizing": "border-box", "textAlign": "center", "borderTopWidth": "1px", "borderTopStyle": "solid", "borderTopColor": var("gutter")}, [text("p", footer.get("message", ""), line, name="Message"), text("p", footer.get("copyright", ""), line, name="Copyright")], name="Footer", visible_if=None),
		]
	)


SCALAR_JS = """const live = typeof window !== "undefined";
if (!live) return;
// Scalar reads markup inside its mount, and treats a data-spec attribute, as the document:
// mount into an empty child and keep the URL in data-openapi-url.
const root = this;
const mount = document.createElement("div");
root.append(mount);
const start = () => {
	root.querySelector(".docs-api-loading")?.remove();
	window.Scalar.createApiReference(mount, {
		url: root.dataset.openapiUrl,
		servers: root.dataset.exampleServer ? [{ url: root.dataset.exampleServer }] : undefined,
		hideClientButton: true,
		hideTestRequestButton: true,
		showDeveloperTools: "never",
		documentDownloadType: "json",
		telemetry: false,
		agent: { disabled: true },
		mcp: { disabled: true },
	});
};
if (window.Scalar) return start();
const tag = document.createElement("script");
tag.src = "https://cdn.jsdelivr.net/npm/@scalar/api-reference@1";
tag.onload = start;
document.head.append(tag);
"""


def api_page() -> dict:
	return body(
		[
			block(
				"div",
				{"width": "100%", "minHeight": "100vh"},
				[text("p", "The API reference loads when the page opens.", {"margin": "0", "padding": "24px", "fontFamily": FONT, "fontSize": "14px", "color": var("text-2")}, name="Loading", bind={"innerHTML": "data.reference_title"}, classes=["docs-api-loading"])],
				name="Scalar",
				attrs={"data-openapi-url": "", "data-example-server": ""},
				bind={"data-openapi-url": "data.spec_url", "data-example-server": "data.server"},
				js=SCALAR_JS,
			)
		],
		{"alignItems": "stretch", "flexWrap": "nowrap"},
	)


# ---------------------------------------------------------------- scripts


def script(template: str, config: dict) -> str:
	return (TEMPLATES / template).read_text().replace("__CONFIG__", repr(config))


def root_entries(spec: Spec) -> list[str]:
	"""Top-level repository entries outside docs_dir: routes starting with them map to the repo root."""
	url = f"https://data.jsdelivr.com/v1/packages/gh/{spec.repository}@{spec.branch}?structure=tree"
	with urllib.request.urlopen(url, timeout=60) as response:
		tree = json.loads(response.read())
	names = []
	for entry in tree.get("files", []):
		name = entry["name"]
		if name.startswith(".") or name == spec.docs_dir:
			continue
		if entry["type"] == "directory" or name.endswith(".md"):
			names.append(name[:-3] if name.endswith(".md") else name)
	return sorted(names)


def doc_config(spec: Spec) -> dict:
	links = spec.data.get("source_links", {})
	return {
		"repository": spec.repository,
		"branch": spec.branch,
		"cdn": spec.cdn,
		"github": spec.github,
		"docs_dir": spec.docs_dir,
		"prefix": spec.prefix,
		"site_title": spec.title,
		"home_source": spec.data.get("home", {}).get("source", f"{spec.docs_dir}/index.md".lstrip("/")),
		"root_entries": root_entries(spec) if spec.docs_dir else [],
		"source_extensions": links.get("extensions", [".go", ".py", ".js", ".ts", ".lua", ".sh", ".toml", ".json", ".yml", ".yaml", ".h", ".c"]),
		"source_directories": links.get("directories", []),
		"sidebars": [[entry["variant"], [spec.route(start) for start in entry.get("prefixes", [f"/{spec.prefix}"])]] for entry in spec.data.get("sidebars", [])],
		"component_id": DOC_COMPONENT,
	}


# ---------------------------------------------------------------- push


class Builder:
	def __init__(self, site: Site, spec: Spec, emit: Path | None):
		self.site, self.spec, self.emit = site, spec, emit
		self.handles: dict[str, str] = {}
		self.tokens: set[str] = set()
		self.components: set[str] = set()

	def upsert_tokens(self) -> None:
		"""Builder names tokens with UUIDs, so ours are found by label (group = site title)."""
		group = self.spec.title
		existing: dict[str, str] = {}
		for row in self.site.names("Builder Token", [["group", "=", group]], ("name", "token_name", "creation")):
			if row["token_name"] in existing:
				self.site.call("DELETE", Site.resource("Builder Token", row["name"]))
			else:
				existing[row["token_name"]] = row["name"]
		for key, label, light, dark in default_tokens(self.spec.data.get("brand", {})):
			values = {"token_name": label, "type": "Color", "value": light, "dark_value": dark, "group": group}
			if self.emit:
				self.handles[key] = existing.get(label, f"token-{key}")
				continue
			if label in existing:
				self.site.call("PUT", Site.resource("Builder Token", existing[label]), values)
			else:
				existing[label] = self.site.call("POST", Site.resource("Builder Token"), values)["data"]["name"]
			self.handles[key] = existing[label]
		self.tokens = {row["name"] for row in self.site.names("Builder Token")} | set(self.handles.values())
		print("tokens", len(self.handles))

	def with_tokens(self, serialized: str) -> str:
		for key in sorted(self.handles, key=len, reverse=True):
			serialized = serialized.replace(f"var(--token-{key})", f"var(--{self.handles[key]})")
		if "var(--token-" in serialized:
			raise SystemExit("unknown token in templates: " + serialized[serialized.index("var(--token-") :][:40])
		return serialized

	def component(self, component_id: str, label: str, root: dict, data_script: str = "") -> None:
		root = normalize(stabilize_ids(copy.deepcopy(root), component_id))
		DEFINITIONS[component_id] = root
		self.components.add(component_id)
		lint("component", component_id, [json.loads(self.with_tokens(json.dumps(root)))], self.tokens, self.components, data_script)
		values = {"component_name": label, "block": self.with_tokens(compact_json(root)), "component_data_script": data_script}
		if self.emit:
			(self.emit / f"{component_id}.json").write_text(json.dumps(root, indent=1))
			(self.emit / f"{component_id}.data_script.py").write_text(data_script)
			return
		if self.site.call("GET", Site.resource("Builder Component", component_id)):
			self.site.call("PUT", Site.resource("Builder Component", component_id), values)
		else:
			self.site.call("POST", Site.resource("Builder Component"), {"component_id": component_id, **values})
		print("component", component_id)

	def page(self, route: str, title: str, tree: dict, data_script: str = "", description: str = "") -> None:
		blocks = [normalize(tree)]
		lint("page", route, json.loads(self.with_tokens(json.dumps(blocks))), self.tokens, self.components)
		values = {"page_title": title, "draft_blocks": self.with_tokens(compact_json(blocks)), "page_data_script": data_script, "meta_description": description}
		if self.emit:
			(self.emit / f"page-{route.replace('/', '_').replace(':', '') or 'home'}.json").write_text(json.dumps(blocks, indent=1))
			if data_script:
				(self.emit / f"page-{route.replace('/', '_').replace(':', '')}.data_script.py").write_text(data_script)
			return
		found = self.site.names("Builder Page", [["route", "=", route]])
		if found:
			name = found[0]["name"]
			self.site.call("PUT", Site.resource("Builder Page", name), values)
		else:
			name = self.site.call("POST", Site.resource("Builder Page"), {"route": route, "published": 0, **values})["data"]["name"]
		# publish reads run_method from the body on current Frappe, not the query string
		self.site.call("POST", Site.resource("Builder Page", name), {"run_method": "publish"})
		print("page", route)

	def clean_routes(self) -> None:
		"""Static pages under the prefix shadow the dynamic shells: a static route always wins."""
		for page in self.site.names("Builder Page", None, ("name", "route", "dynamic_route")):
			if not page["dynamic_route"] and (page["route"] == self.spec.prefix or page["route"].startswith(self.spec.prefix + "/")):
				self.site.call("DELETE", Site.resource("Builder Page", page["name"]))
				print("deleted static page", page["route"])

	def run(self, clean: bool) -> None:
		spec = self.spec
		self.components = {row["name"] for row in self.site.names("Builder Component")}
		self.upsert_tokens()
		if not self.emit:
			head = (f'<link rel="icon" href="{spec.logo}">\n' if spec.logo else "") + '<script>(()=>{const t=localStorage.getItem("docs-theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t})();</script>'
			self.site.call("PUT", Site.resource("Builder Settings", "Builder Settings"), {"head_html": head, "disable_auto_dark_mode": 0, "home_page": "home"})
			if clean:
				self.clean_routes()
		config = doc_config(spec)
		self.component(NAV_COMPONENT, "Doc Navbar", navbar(spec))
		self.component(DOC_COMPONENT, "Doc Page", doc_page(spec), script("doc_data_script.py", config))
		for depth in range(1, 6):
			route = spec.prefix + "/" + "/".join(f":p{i}" for i in range(1, depth + 1))
			self.page(route, spec.title, page_body([sticky_navbar(), instance(DOC_COMPONENT)]))
		home_config = {key: config[key] for key in ("cdn", "home_source", "docs_dir", "prefix", "site_title")}
		self.page("home", spec.title, home_page(spec), script("home_data_script.py", home_config), spec.data.get("description", ""))
		references = {entry["name"]: {"title": entry["title"], "spec": entry["spec"], "server": entry.get("server", "")} for entry in spec.data.get("api_references", [])}
		if references:
			api_config = {"references": references, "default": next(iter(references)), "cdn": spec.cdn, "site_title": spec.title}
			self.page(API_COMPONENT_PAGE, f"API reference · {spec.title}", api_page(), script("api_data_script.py", api_config))


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("spec")
	parser.add_argument("--emit", type=Path, help="write generated trees and scripts here; push nothing")
	parser.add_argument("--clean-routes", action="store_true", help="delete static pages under the docs prefix")
	args = parser.parse_args()
	spec = Spec(json.loads(Path(args.spec).read_text()))
	if args.emit:
		args.emit.mkdir(parents=True, exist_ok=True)
	Builder(Site(spec.data["site"]), spec, args.emit).run(args.clean_routes)


if __name__ == "__main__":
	main()
