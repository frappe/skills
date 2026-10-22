# Renders one docs page from its Markdown in the GitHub repository (through jsDelivr).
# The route variables p1..p5 name the page; the editor preview uses the preview_route prop.
# Needs server scripts enabled (frappe.utils.md_to_html). No imports, no regex, and a def
# can't see top-level names, so everything lives inside main() and CONFIG is passed in.


def main(props, component, CONFIG):
	CDN = CONFIG["cdn"]
	GITHUB = CONFIG["github"]
	BRANCH = CONFIG["branch"]
	DOCS_DIR = CONFIG["docs_dir"]
	PREFIX = CONFIG["prefix"]
	ROOT_ENTRIES = CONFIG["root_entries"]
	SOURCE_EXTENSIONS = CONFIG["source_extensions"]
	SOURCE_DIRECTORIES = CONFIG["source_directories"]
	SIDEBARS = CONFIG["sidebars"]
	SLUG_SEPARATORS = " \t\n~`!@#$%^&*()-_+=[]{}|\\;:\"'“”‘’<>,.?/"
	CONTAINERS = {"info": "INFO", "tip": "TIP", "warning": "WARNING", "danger": "DANGER", "details": "Details"}
	DIAGRAMS = {"sequenceDiagram": "Sequence diagram", "stateDiagram-v2": "State diagram", "stateDiagram": "State diagram", "flowchart": "Flow diagram", "graph": "Flow diagram"}

	def escape(text):
		return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

	def strip_tags(html):
		out = ""
		inside = False
		for character in html:
			if character == "<":
				inside = True
			elif character == ">":
				inside = False
			elif not inside:
				out += character
		return out.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'").strip()

	# VitePress (@mdit-vue) slugify, so anchors and cross-page links match the handbook.
	def slugify(text):
		out = ""
		for character in text:
			if character in SLUG_SEPARATORS or character.isspace() or ord(character) < 32:
				if not out.endswith("-"):
					out += "-"
			else:
				out += character
		out = out.strip("-").lower()
		if out and out[0].isdigit():
			out = "_" + out
		return out

	def fetch(path):
		return frappe.make_get_request(CDN + path)

	def route_for(path):
		"""Repository path (with or without .md) to this site's route."""
		path = path.split("#")[0]
		if path.endswith(".md"):
			path = path[:-3]
		for index_name in ["README", "index"]:
			if path == index_name:
				path = ""
			elif path.endswith("/" + index_name):
				path = path[: -len(index_name) - 1]
		path = path.strip("/")
		if DOCS_DIR and (path == DOCS_DIR or path.startswith(DOCS_DIR + "/")):
			path = path[len(DOCS_DIR) + 1 :]
		return "/" + PREFIX + "/" + path if path else "/"

	def resolve(base_directory, href):
		parts = [part for part in base_directory.split("/") if part]
		for part in href.split("/"):
			if part == "..":
				if parts:
					parts.pop()
			elif part and part != ".":
				parts.append(part)
		return "/".join(parts) + ("/" if href.endswith("/") else "")

	def rewrite_link(href, base_directory):
		if href.startswith("#") or "://" in href or href.startswith("mailto:") or href.startswith("//"):
			return href
		fragment = ""
		if "#" in href:
			fragment = "#" + href.split("#", 1)[1]
			href = href.split("#", 1)[0]
		if href.startswith("/api/"):
			name = href.strip("/").split("/")[1] if len(href.strip("/").split("/")) > 1 else ""
			return "/api-reference/" + name
		if href.startswith("/"):
			return route_for(href.strip("/")) + fragment
		path = resolve(base_directory, href)
		is_source_file = any([path.endswith(extension) for extension in SOURCE_EXTENSIONS]) or path.endswith("/Makefile") or path.endswith("/authorized-keys-command")
		is_source_directory = path.endswith("/") and any([path.startswith(directory) for directory in SOURCE_DIRECTORIES])
		if is_source_file or is_source_directory:
			return GITHUB + ("tree" if is_source_directory else "blob") + "/" + BRANCH + "/" + path + fragment
		return route_for(path) + fragment

	def rewrite_attribute(html, attribute, transform):
		marker = attribute + '="'
		out = ""
		position = 0
		while True:
			start = html.find(marker, position)
			if start < 0:
				break
			end = html.find('"', start + len(marker))
			value = html[start + len(marker) : end]
			out += html[position : start + len(marker)] + transform(value)
			position = end
		return out + html[position:]

	def locate(route_parts):
		"""Find the Markdown file for a route without probing for 404s: read jsDelivr's listings."""
		if not route_parts:
			return CONFIG["home_source"]
		base = "/".join(route_parts)
		if DOCS_DIR and route_parts[0] not in ROOT_ENTRIES:
			base = DOCS_DIR + "/" + base
		parent = base.rsplit("/", 1)[0] + "/" if "/" in base else ""
		listing = fetch(parent) or ""
		marker = "@" + BRANCH + "/"
		if (marker + base + '.md"') in listing:
			return base + ".md"
		if (marker + base + '/"') in listing:
			inner = fetch(base + "/") or ""
			for name in ["index.md", "README.md"]:
				if (marker + base + "/" + name + '"') in inner:
					return base + "/" + name
		return None

	def split_blocks(markdown):
		"""Pull ::: containers and mermaid fences out of the Markdown, so md_to_html renders
		them as VitePress does. Returns the outer Markdown and the HTML for each placeholder."""
		lines = markdown.split("\n")
		outer = []
		blocks = []
		index = 0
		fence = ""
		while index < len(lines):
			line = lines[index]
			stripped = line.strip()
			if fence:
				outer.append(line)
				if stripped.startswith(fence):
					fence = ""
				index += 1
				continue
			if stripped.startswith("```mermaid"):
				source = []
				index += 1
				while index < len(lines) and not lines[index].strip().startswith("```"):
					source.append(lines[index])
					index += 1
				text = "\n".join(source)
				kind = text.strip().split()[0] if text.strip() else ""
				label = DIAGRAMS.get(kind, "Diagram")
				extra = " is-sequence" if kind == "sequenceDiagram" else (" is-flowchart" if kind in ["flowchart", "graph"] else "")
				blocks.append(
					'<figure class="diagram-frame' + extra + '" aria-label="' + label + '" data-diagram>'
					+ '<div class="diagram-toolbar"><span>' + label + '</span><button type="button" aria-expanded="false" aria-label="Expand diagram">Expand</button></div>'
					+ '<pre class="diagram-source">' + escape(text) + "</pre></figure>"
				)
				outer.extend(["", "DOCSBLOCK" + str(len(blocks) - 1) + "DOCSBLOCK", ""])
				index += 1
				continue
			if stripped.startswith("```") or stripped.startswith("~~~"):
				fence = stripped[:3]
				outer.append(line)
				index += 1
				continue
			if stripped.startswith(":::"):
				words = stripped[3:].strip().split(" ", 1)
				kind = words[0].lower() if words else ""
				if kind in CONTAINERS:
					title = words[1].strip() if len(words) > 1 and words[1].strip() else CONTAINERS[kind]
					body = []
					depth = 1
					index += 1
					inner_fence = ""
					while index < len(lines):
						inner = lines[index].strip()
						if inner_fence:
							if inner.startswith(inner_fence):
								inner_fence = ""
						elif inner.startswith("```") or inner.startswith("~~~"):
							inner_fence = inner[:3]
						elif inner.startswith(":::") and inner[3:].strip():
							depth += 1
						elif inner == ":::":
							depth -= 1
							if depth == 0:
								break
						body.append(lines[index])
						index += 1
					rendered = frappe.utils.md_to_html("\n".join(body)) or ""
					title_html = frappe.utils.md_to_html(title) or escape(title)
					title_html = title_html.strip()
					if title_html.startswith("<p>") and title_html.endswith("</p>"):
						title_html = title_html[3:-4]
					if kind == "details":
						html = '<details class="details custom-block"><summary>' + title_html + "</summary>" + rendered + "</details>"
					else:
						html = '<div class="' + kind + ' custom-block"><p class="custom-block-title">' + title_html + "</p>" + rendered + "</div>"
					blocks.append(html)
					outer.extend(["", "DOCSBLOCK" + str(len(blocks) - 1) + "DOCSBLOCK", ""])
					index += 1
					continue
			outer.append(line)
			index += 1
		return ["\n".join(outer), blocks]

	def anchor_headings(html):
		"""Give each heading the VitePress id and permalink, and collect the outline."""
		out = ""
		position = 0
		used = {}
		outline = []
		title = ""
		while True:
			start = -1
			level = ""
			for candidate in ["1", "2", "3", "4", "5", "6"]:
				found = html.find("<h" + candidate, position)
				if found >= 0 and (start < 0 or found < start):
					start = found
					level = candidate
			if start < 0:
				break
			open_end = html.find(">", start)
			close = html.find("</h" + level + ">", open_end)
			inner = html[open_end + 1 : close]
			text = strip_tags(inner)
			slug = slugify(text)
			if slug in used:
				used[slug] = used[slug] + 1
				slug = slug + "-" + str(used[slug])
			else:
				used[slug] = 0
			if level == "1" and not title:
				title = text
			if level == "2":
				outline.append({"text": text, "href": "#" + slug})
			out += html[position:start]
			out += "<h" + level + ' id="' + slug + '" tabindex="-1">' + inner
			out += ' <a class="header-anchor" href="#' + slug + '" aria-label="Permalink to &quot;' + escape(text) + '&quot;">&#8203;</a></h' + level + ">"
			position = close + len("</h" + level + ">")
		return [out + html[position:], outline, title]

	def frame_code(html):
		"""Wrap md_to_html code blocks in the VitePress code-block markup."""
		out = ""
		position = 0
		while True:
			start = html.find("<pre><code", position)
			if start < 0:
				break
			tag_end = html.find(">", start + 5)
			tag = html[start + 5 : tag_end]
			language = ""
			if "language-" in tag:
				language = tag.split("language-", 1)[1].split('"')[0].split(" ")[0]
			end = html.find("</code></pre>", tag_end) + len("</code></pre>")
			label = language or "txt"
			out += html[position:start]
			out += '<div class="language-' + label + ' vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">' + label + "</span>"
			out += '<pre class="vp-code"><code data-language="' + language + '"' + html[tag_end:end].replace("</code></pre>", "</code></pre></div>", 1)
			position = end
		return out + html[position:]

	def reading_order(wanted):
		"""Prev and next follow the sidebar this component shows, so editing it in Builder reorders them."""
		rows = frappe.db.get_all("Builder Component", filters={"name": CONFIG["component_id"]}, fields=["block"])
		if not rows:
			return []
		root = json.loads(rows[0]["block"] or "{}")
		links = []
		stack = [[root, False]]
		while stack:
			entry = stack.pop()
			node = entry[0]
			inside = entry[1] or (node.get("customAttributes") or {}).get("data-sidebar-variant") == wanted
			href = (node.get("attributes") or {}).get("href")
			if inside and href and "data-sidebar-link" in (node.get("customAttributes") or {}) and not (node.get("attributes") or {}).get("target"):
				links.append({"title": strip_tags(node.get("innerHTML") or ""), "href": href})
			for child in list(node.get("children") or [])[::-1]:
				stack.append([child, inside])
		return links

	route_parts = [frappe.form_dict.get(key) for key in ["p1", "p2", "p3", "p4", "p5"] if frappe.form_dict.get(key)]
	if not route_parts:
		preview = str(props.get("preview_route") or "").strip("/")
		route_parts = [part for part in preview.split("/") if part]
		if route_parts and route_parts[0] == PREFIX:
			route_parts = route_parts[1:]
	route = "/" + PREFIX + "/" + "/".join(route_parts)

	# The sidebar whose route prefix matches best is shown; each has a show_<variant> flag.
	variant = SIDEBARS[0][0] if SIDEBARS else ""
	matched = -1
	for sidebar in SIDEBARS:
		for start in sidebar[1]:
			if (route == start or route.startswith(start.rstrip("/") + "/")) and len(start) > matched:
				matched = len(start)
				variant = sidebar[0]
	for sidebar in SIDEBARS:
		component["show_" + sidebar[0]] = sidebar[0] == variant

	component.route = route
	component.not_found = False
	component.content_html = ""
	component.outline = []
	component.has_outline = False
	component.title = CONFIG["site_title"]

	source = None
	try:
		source = locate(route_parts)
	except Exception:
		source = None
	if not source:
		component.not_found = True
		component.content_html = '<h1 id="page-not-found">Page not found</h1><p>No page in the <a href="' + GITHUB + "tree/" + BRANCH + '">' + CONFIG["repository"] + "</a> repository matches <code>" + escape(route) + "</code>.</p>"
		component.component_data = {"route": route, "title": "Page not found", "site_title": CONFIG["site_title"]}
		return

	markdown = fetch(source) or ""
	if markdown.startswith("---"):
		closing = markdown.find("\n---", 3)
		if closing > 0:
			markdown = markdown[closing + 4 :]
	split = split_blocks(markdown)
	html = frappe.utils.md_to_html(split[0]) or ""
	for number, block_html in enumerate(split[1]):
		marker = "DOCSBLOCK" + str(number) + "DOCSBLOCK"
		html = html.replace("<p>" + marker + "</p>", block_html).replace(marker, block_html)
	headings = anchor_headings(html)
	html = frame_code(headings[0])
	base_directory = source.rsplit("/", 1)[0] if "/" in source else ""
	html = rewrite_attribute(html, "href", lambda value: rewrite_link(value, base_directory))
	html = rewrite_attribute(html, "src", lambda value: value if "://" in value or value.startswith("data:") else CDN + resolve(base_directory, value))
	html = html.replace(' class="table table-bordered"', "")

	order = reading_order(variant)
	here = -1
	for position, link in enumerate(order):
		if link["href"].rstrip("/") == route.rstrip("/"):
			here = position
	previous_link = order[here - 1] if here > 0 else None
	next_link = order[here + 1] if 0 <= here < len(order) - 1 else None

	component.title = headings[2] or route_parts[-1]
	component.content_html = html
	component.outline = headings[1]
	component.has_outline = len(headings[1]) > 0
	component.has_prev = bool(previous_link)
	component.prev_title = previous_link["title"] if previous_link else ""
	component.prev_href = previous_link["href"] if previous_link else ""
	component.has_next = bool(next_link)
	component.next_title = next_link["title"] if next_link else ""
	component.next_href = next_link["href"] if next_link else ""
	component.has_pager = bool(previous_link or next_link)
	component.source_url = GITHUB + "blob/" + BRANCH + "/" + source
	component.component_data = {"route": route, "title": component.title, "source": source, "site_title": CONFIG["site_title"]}


main(props, component, __CONFIG__)
