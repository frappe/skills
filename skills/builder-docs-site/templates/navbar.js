// Site chrome: active nav item, System flyout, appearance switch, mobile menu, and search.
// Search indexes the handbook straight from GitHub, so new pages are searchable without a rebuild.
const live = typeof window !== "undefined";
const root = this;
const repository = props.repository;
const branch = props.branch || "main";
const docsDir = (props.docs_dir || "").replace(/\/$/, "");
const prefix = (props.route_prefix || "docs").replace(/^\/|\/$/g, "");

for (const item of root.querySelectorAll("[data-active-match]")) {
	const pattern = new RegExp(item.dataset.activeMatch);
	item.classList.toggle("active", live && pattern.test(location.pathname));
}
if (!live) return;

// Builder's theme hook: data-theme on <html> sets color-scheme, and every token follows it.
const html = document.documentElement;
const isDark = () => (html.dataset.theme ? html.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches);
const switchButton = root.querySelector("[data-appearance]");
switchButton?.setAttribute("aria-checked", String(isDark()));
switchButton?.addEventListener("click", () => {
	const dark = !isDark();
	html.dataset.theme = dark ? "dark" : "light";
	localStorage.setItem("docs-theme", html.dataset.theme);
	switchButton.setAttribute("aria-checked", String(dark));
});

const flyout = root.querySelector("[data-flyout]");
flyout?.querySelector("button")?.addEventListener("click", () => {
	const open = flyout.classList.toggle("open");
	flyout.querySelector("button").setAttribute("aria-expanded", String(open));
});
document.addEventListener("click", (event) => {
	if (flyout && !flyout.contains(event.target)) flyout.classList.remove("open");
});

root.querySelector("[data-menu-toggle]")?.addEventListener("click", () => window.events?.dispatch("docs:sidebar-toggle"));

// ---------------------------------------------------------------- search

const rawUrl = (path) => `https://raw.githubusercontent.com/${repository}/${branch}/${path}`;
const EXCLUDED = /(^|\/)(CLAUDE|AGENTS)\.md$|^README\.md$|^report\.md$|(^|\/)(node_modules|docs-build|\.tmp|\.vitepress|\.github)\//;

// Files under docs_dir are served at /<prefix>/<rest>; other repository files at /<prefix>/<path>.
function routeForPath(path) {
	let route = path.replace(/\.md$/i, "").replace(/(^|\/)(README|index)$/, "$1").replace(/\/$/, "");
	if (docsDir && (route === docsDir || route.startsWith(docsDir + "/"))) route = route.slice(docsDir.length + 1);
	return route ? `/${prefix}/${route}` : "/";
}

function slugify(text) {
	return text
		.normalize("NFKD")
		.replace(/[̀-ͯ]/g, "")
		.replace(/[\u0000-\u001f]/g, "")
		.replace(/[\s~`!@#$%^&*()\-_+=[\]{}|\\;:"'“”‘’<>,.?/]+/g, "-")
		.replace(/-{2,}/g, "-")
		.replace(/^-+|-+$/g, "")
		.replace(/^(\d)/, "_$1")
		.toLowerCase();
}

function plain(markdown) {
	return markdown
		.replace(/```[\s\S]*?```/g, " ")
		.replace(/<[^>]+>/g, " ")
		.replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
		.replace(/[`*_>#|:-]+/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}

function sections(path, markdown) {
	const body = markdown.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, "");
	const route = routeForPath(path);
	const title = body.match(/^#\s+(.+)$/m)?.[1].trim() || route;
	const result = [];
	let current = { title, heading: "", anchor: "", lines: [] };
	let fenced = false;
	for (const line of body.split("\n")) {
		if (/^\s*```/.test(line)) fenced = !fenced;
		const match = !fenced && line.match(/^(#{1,3})\s+(.+)$/);
		if (match) {
			result.push(current);
			const heading = match[2].replace(/`/g, "").trim();
			current = { title, heading: match[1].length === 1 ? "" : heading, anchor: match[1].length === 1 ? "" : slugify(heading), lines: [] };
		} else current.lines.push(line);
	}
	result.push(current);
	return result
		.map((section) => ({ route, title: section.title, heading: section.heading, anchor: section.anchor, text: plain(section.lines.join("\n")) }))
		.filter((section) => section.heading || section.text);
}

let indexPromise;
function loadIndex() {
	indexPromise ||= (async () => {
		const cacheKey = `docs-search:${repository}:${branch}`;
		const cached = sessionStorage.getItem(cacheKey);
		if (cached) return JSON.parse(cached);
		const tree = await (await fetch(`https://api.github.com/repos/${repository}/git/trees/${branch}?recursive=1`)).json();
		const paths = (tree.tree || []).map((entry) => entry.path).filter((path) => path.endsWith(".md") && !EXCLUDED.test(path));
		const files = await Promise.all(paths.map(async (path) => [path, await (await fetch(rawUrl(path))).text()]));
		const index = files.flatMap(([path, markdown]) => sections(path, markdown));
		try {
			sessionStorage.setItem(cacheKey, JSON.stringify(index));
		} catch {}
		return index;
	})();
	return indexPromise;
}

function search(index, query) {
	const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
	if (!terms.length) return [];
	const scored = [];
	for (const entry of index) {
		const title = entry.title.toLowerCase();
		const heading = entry.heading.toLowerCase();
		const text = entry.text.toLowerCase();
		let score = 0;
		for (const term of terms) {
			const inTitle = title.includes(term);
			const inHeading = heading.includes(term);
			const inText = text.includes(term);
			if (!inTitle && !inHeading && !inText) {
				score = 0;
				break;
			}
			score += (inTitle ? 6 : 0) + (inHeading ? 4 : 0) + (inText ? 1 : 0);
		}
		if (score) scored.push({ entry, score });
	}
	return scored.sort((a, b) => b.score - a.score).slice(0, 30).map((item) => item.entry);
}

function snippet(text, query) {
	const term = query.toLowerCase().split(/\s+/).find(Boolean) || "";
	const at = Math.max(0, text.toLowerCase().indexOf(term) - 40);
	return (at ? "…" : "") + text.slice(at, at + 140) + (text.length > at + 140 ? "…" : "");
}

const modal = document.createElement("div");
modal.className = "docs-search-modal";
modal.hidden = true;
modal.setAttribute("role", "dialog");
modal.setAttribute("aria-modal", "true");
modal.setAttribute("aria-label", "Search");
const backdrop = document.createElement("div");
backdrop.className = "docs-search-backdrop";
const panel = document.createElement("div");
panel.className = "docs-search-panel";
const form = document.createElement("form");
form.className = "docs-search-form";
const icon = document.createElement("span");
icon.className = "vpi-search docs-search-form-icon";
const input = document.createElement("input");
input.type = "search";
input.placeholder = "Search docs";
input.setAttribute("aria-label", "Search docs");
input.autocomplete = "off";
form.append(icon, input);
const results = document.createElement("ul");
results.className = "docs-search-results";
results.setAttribute("role", "listbox");
const status = document.createElement("p");
status.className = "docs-search-status";
const hint = document.createElement("div");
hint.className = "docs-search-hint";
for (const [keys, label] of [["↑ ↓", "to navigate"], ["↵", "to select"], ["esc", "to close"]]) {
	const key = document.createElement("kbd");
	key.textContent = keys;
	const text = document.createElement("span");
	text.textContent = label;
	hint.append(key, text);
}
panel.append(form, status, results, hint);
modal.append(backdrop, panel);
root.append(modal);

let selected = 0;
let index = [];
const render = () => {
	const query = input.value.trim();
	const found = query ? search(index, query) : [];
	selected = Math.min(selected, Math.max(found.length - 1, 0));
	status.textContent = !index.length ? "Indexing the handbook from GitHub…" : query && !found.length ? `No results for "${query}"` : "";
	results.replaceChildren(
		...found.map((entry, position) => {
			const item = document.createElement("li");
			const link = document.createElement("a");
			link.href = entry.route + (entry.anchor ? `#${entry.anchor}` : "");
			link.className = position === selected ? "selected" : "";
			link.setAttribute("role", "option");
			const titles = document.createElement("span");
			titles.className = "docs-search-titles";
			titles.textContent = entry.heading ? `${entry.title} › ${entry.heading}` : entry.title;
			const excerpt = document.createElement("span");
			excerpt.className = "docs-search-excerpt";
			excerpt.textContent = snippet(entry.text, query);
			link.append(titles, excerpt);
			item.append(link);
			return item;
		})
	);
	results.querySelector(".selected")?.scrollIntoView({ block: "nearest" });
};

const open = async () => {
	modal.hidden = false;
	document.body.style.overflow = "hidden";
	input.focus();
	input.select();
	render();
	try {
		index = await loadIndex();
	} catch {
		status.textContent = "Search is unavailable: GitHub did not answer.";
		return;
	}
	render();
};
const close = () => {
	modal.hidden = true;
	document.body.style.overflow = "";
};

root.querySelector("[data-search-open]")?.addEventListener("click", open);
backdrop.addEventListener("click", close);
input.addEventListener("input", () => {
	selected = 0;
	render();
});
form.addEventListener("submit", (event) => {
	event.preventDefault();
	results.querySelector(".selected")?.click();
});
modal.addEventListener("keydown", (event) => {
	const count = results.children.length;
	if (event.key === "ArrowDown" && count) selected = (selected + 1) % count;
	else if (event.key === "ArrowUp" && count) selected = (selected - 1 + count) % count;
	else if (event.key === "Escape") return close();
	else return;
	event.preventDefault();
	render();
});
results.addEventListener("click", (event) => {
	if (event.target.closest("a")) close();
});
document.addEventListener("keydown", (event) => {
	const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
	if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !typing)) {
		event.preventDefault();
		modal.hidden ? open() : close();
	}
});
