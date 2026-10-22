// Doc Page: the server renders the page; this script marks the sidebar and adds what
// needs a browser: code highlighting, Mermaid diagrams, copy buttons and the outline spy.
const live = typeof window !== "undefined";
const root = this;
const route = (component_data && component_data.route) || "";

// Paint first, from server data, so the editor canvas shows the same state.
for (const link of root.querySelectorAll("a[data-sidebar-link]")) {
	const active = link.getAttribute("href") === route;
	link.classList.toggle("active", active);
	if (!active) continue;
	for (let group = link.closest("[data-sidebar-group]"); group; group = group.parentElement && group.parentElement.closest("[data-sidebar-group]")) {
		group.classList.remove("collapsed");
		group.classList.add("has-active");
	}
}
if (!live) return;

if (component_data.title) document.title = `${component_data.title} | ${component_data.site_title}`;
const content = root.querySelector(".docs-content");

// ---------------------------------------------------------------- sidebar

root.addEventListener("click", (event) => {
	const toggle = event.target.closest("[data-sidebar-toggle]");
	if (toggle) toggle.closest("[data-sidebar-group]").classList.toggle("collapsed");
	if (event.target.closest("a[data-sidebar-link]") || event.target.closest(".docs-sidebar-backdrop")) root.classList.remove("sidebar-open");
});
root.addEventListener("keydown", (event) => {
	const toggle = event.target.closest("[data-sidebar-toggle]");
	if (toggle && (event.key === "Enter" || event.key === " ")) {
		event.preventDefault();
		toggle.click();
	}
});
window.events?.listen("docs:sidebar-toggle", () => root.classList.toggle("sidebar-open"));
document.addEventListener("keydown", (event) => {
	if (event.key === "Escape") root.classList.remove("sidebar-open");
});
const activeLink = root.querySelector("a[data-sidebar-link].active");
const panel = activeLink?.closest(".docs-sidebar");
if (panel) panel.scrollTop = activeLink.offsetTop - panel.clientHeight / 2;

// ---------------------------------------------------------------- outline spy

const headings = [...content.querySelectorAll("h2[id]")];
const outlineLinks = [...root.querySelectorAll(".docs-outline-link")];
const spy = () => {
	let current = null;
	for (const heading of headings) if (heading.getBoundingClientRect().top < 120) current = heading.id;
	for (const link of outlineLinks) link.classList.toggle("active", link.getAttribute("href") === `#${current}`);
};
addEventListener("scroll", spy, { passive: true });
spy();

// ---------------------------------------------------------------- copy buttons

content.addEventListener("click", async (event) => {
	const button = event.target.closest("button.copy");
	if (!button) return;
	await navigator.clipboard.writeText(button.parentElement.querySelector("code").innerText.replace(/\n$/, ""));
	button.classList.add("copied");
	setTimeout(() => button.classList.remove("copied"), 2000);
});

// ---------------------------------------------------------------- code highlighting (best effort)

const ALIASES = { sh: "shellscript", bash: "shellscript", shell: "shellscript", console: "shellscript", py: "python", yml: "yaml", js: "javascript", ts: "typescript" };
const SUPPORTED = ["go", "shellscript", "python", "json", "toml", "sql", "http", "yaml", "lua", "javascript", "typescript", "ini", "diff", "c", "makefile"];
const blocks = [...content.querySelectorAll("pre.vp-code > code[data-language]")]
	.map((code) => ({ code, language: ALIASES[code.dataset.language] || code.dataset.language }))
	.filter((block) => SUPPORTED.includes(block.language));
if (blocks.length) {
	try {
		window.docsHighlighter ||= import("https://esm.sh/shiki@3.13.0").then((shiki) =>
			shiki.createHighlighter({ themes: ["github-light", "github-dark"], langs: [] })
		);
		const highlighter = await window.docsHighlighter;
		const languages = [...new Set(blocks.map((block) => block.language))];
		await Promise.all(languages.map((language) => highlighter.loadLanguage(language).catch(() => null)));
		const loaded = highlighter.getLoadedLanguages();
		for (const block of blocks) {
			if (!loaded.includes(block.language)) continue;
			const html = highlighter.codeToHtml(block.code.textContent.replace(/\n$/, ""), {
				lang: block.language,
				themes: { light: "github-light", dark: "github-dark" },
				defaultColor: false,
			});
			const highlighted = new DOMParser().parseFromString(html, "text/html").querySelector("pre > code");
			if (highlighted) block.code.replaceChildren(...highlighted.childNodes);
		}
	} catch {
		window.docsHighlighter = null;
	}
}

// ---------------------------------------------------------------- Mermaid diagrams

const frames = [...content.querySelectorAll("figure[data-diagram]")];
const isDark = () => {
	const theme = document.documentElement.dataset.theme;
	return theme ? theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
};
const renderDiagrams = async () => {
	if (!frames.length) return;
	let mermaid;
	try {
		mermaid = (await import("https://cdn.jsdelivr.net/npm/mermaid@11.12.0/dist/mermaid.esm.min.mjs")).default;
	} catch {
		return;
	}
	mermaid.initialize({
		startOnLoad: false,
		securityLevel: "strict",
		theme: isDark() ? "dark" : "neutral",
		themeVariables: { fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif" },
		flowchart: { htmlLabels: true, useMaxWidth: true, nodeSpacing: 32, rankSpacing: 40 },
		sequence: { useMaxWidth: true, wrap: true, width: 140, actorMargin: 40, mirrorActors: false },
	});
	for (const frame of frames) {
		const source = frame.querySelector(".diagram-source");
		try {
			const { svg } = await mermaid.render(`docs-diagram-${crypto.randomUUID()}`, source.textContent);
			const canvas = document.createElement("div");
			canvas.className = "diagram-canvas";
			const parsed = new DOMParser().parseFromString(svg, "image/svg+xml").documentElement;
			const width = parsed.viewBox?.baseVal?.width;
			if (width) parsed.setAttribute("width", `${Math.ceil(width)}px`);
			canvas.append(document.importNode(parsed, true));
			frame.querySelector(".diagram-canvas")?.remove();
			frame.append(canvas);
			frame.classList.add("is-rendered");
			frame.classList.toggle("is-fitted", frame.classList.contains("is-flowchart") && innerWidth > 768 && width <= canvas.clientWidth * 1.4);
		} catch {
			frame.classList.add("has-error");
		}
	}
};
content.addEventListener("click", (event) => {
	const button = event.target.closest(".diagram-toolbar button");
	if (!button) return;
	const frame = button.closest(".diagram-frame");
	const expanded = frame.classList.toggle("is-expanded");
	button.textContent = expanded ? "Close" : "Expand";
	button.setAttribute("aria-expanded", String(expanded));
	document.body.classList.toggle("has-expanded-diagram", expanded);
});
document.addEventListener("keydown", (event) => {
	if (event.key === "Escape") content.querySelector(".diagram-frame.is-expanded .diagram-toolbar button")?.click();
});
renderDiagrams();
new MutationObserver(renderDiagrams).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderDiagrams);
