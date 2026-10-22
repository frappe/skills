# Traps

Each entry: symptom → cause → what the design does. Verified on Builder 1.36 (master) with Frappe develop (v17) on a Pilot bench.

## Page rendering

- **Page 417/500 "Illegal template".** Builder renders block text, component scripts and styles, and `head_html` as Jinja, and Frappe rejects any template containing `.__`, even inside `{% raw %}`. Script globals use plain names (`window.docsHighlighter`); keep `.__`, `{{`, `{%`, `{#` out of templates.
- **A static page shadows the shells.** A static route beats a dynamic one, so an old `docs/x/y` page wins over `docs/:p1/:p2`. `build.py --clean-routes` deletes static pages under the prefix.
- **One template cannot match every depth.** A route variable (`:p1` → `<p1>`) matches one segment, and route validation rejects Werkzeug converters such as `<path:x>`. Hence five shells. A root catch-all (`:slug`) would capture `/login` and `/builder`; keep the prefix.
- **`publish` via REST returns KeyError 'run_method'.** Current Frappe reads it from the body: POST `/api/resource/Builder Page/<name>` with `{"run_method": "publish"}`.
- **`<title>` stays the page title.** Only a page data script sets `data.title`; the template's client script sets `document.title` from `component_data.title`.

## Editor canvas

- **Colours missing in the canvas.** Styles that depend on CSS loaded through `head_html` or Builder Settings exist only live. Everything visible uses Builder Tokens (`var(--<token uuid>)`) and block styles or the component's scoped CSS, which the canvas also applies.
- **Bound HTML empty in the canvas.** A bound `innerHTML` renders in the canvas only on a text element. The content blocks are `p`; published pages render `p` as `div`, so block HTML is valid there.
- **Hidden variants still take space.** The canvas dims a block whose visibility condition is false instead of removing it. Both sidebar navigations sit inside one sidebar column, so the dimmed one adds height, not a column.
- **Script throws in the canvas.** The sandbox blocks `window`, `setTimeout`, `document.createElement`, `innerHTML` writes and click listeners. Scripts paint from props and `component_data` first (classList works), then return behind `typeof window !== "undefined"`.

## Tokens

- **`var(--my-name)` resolves to nothing.** Builder Token names are UUIDs: Frappe drops a supplied `name` (autoname is a script) and the token's `token_name` is only a label. `build.py` finds tokens by label within `group = spec.title`, keeps one per label, and swaps `var(--token-<key>)` for `var(--<uuid>)` on push.
- **Dark mode.** Tokens render as `light-dark(light, dark)`, which follows `color-scheme`; Builder's page template maps `data-theme` on `<html>` to it. `disable_auto_dark_mode` must stay 0. Shiki spans use `light-dark(var(--shiki-light), var(--shiki-dark))`.

## Data scripts (safe_exec with server scripts on)

- **`NameError` for a builtin.** Builtins are RestrictedPython's `safe_builtins` plus Frappe's list (`all any dict enumerate list max min range set sorted sum tuple`…): no `reversed`, `zip` only from safe_builtins. `sandbox.py` uses the same set.
- **Compile errors.** No imports, no regex module, no names starting with `_`, no tuple assignment (`a, b = x`; loop unpacking is fine), no augmented assignment to items (`d[k] += 1`).
- **Helpers cannot see top-level names.** Script locals are not a def's globals: everything lives inside `main(...)`, nested helpers close over it, and config is a literal passed in.
- **Fetched Markdown arrives as a dict.** `frappe.make_get_request` returns `parse_qs(text)` for exactly `text/plain; charset=utf-8`, which raw.githubusercontent.com sends. jsDelivr serves `.md` as `text/markdown` (but `.mts`/`.ts` as text/plain), so content comes from `cdn.jsdelivr.net/gh/<repo>@<branch>/`.
- **404 probes fill the Error Log.** `make_request` logs every failed request. The script reads jsDelivr's directory listing to pick `x.md`, `x/index.md` or `x/README.md` (both conventions occur in one repo) instead of trying them.
- **md_to_html is not VitePress.** It knows fenced code, tables and header ids. The script pulls `::: info|tip|warning|danger|details` containers and mermaid fences out first, renders container bodies separately, re-slugs headings the VitePress way, and rewrites links (`.md` → routes, source files → GitHub blob/tree).

## Components

- **Instance renders empty.** Instances need skeleton children; the kit's `instance()` builds them from the definition, and ids come from `stabilize_ids` (block names), so keep block names when editing.
- **Prev/next.** The data script reads the Doc Page definition (`frappe.db.get_all("Builder Component", ...)`) and walks the links of the matching `data-sidebar-variant`, so reordering the sidebar in the editor reorders the pager.
- **A component save that never shows.** Publishing queues background renders; a component saved during one can be cached in its old version. Components are saved before pages in a run; wait ~15 s after publishing before saving a component again.

## Scalar (API references)

- **"Invalid YAML object", hydration mismatch.** Scalar parses markup inside its mount, and a `data-spec` attribute, as the document. Mount into an empty child created by the script; keep the URL in `data-openapi-url`.
- **A spec 404s.** Some specs are generated at build time and only exist on the deployed site (Atlas: Metal). Point `spec` at the published URL (`--published` in `spec_from_vitepress.py`).

## Platform noise

- **Error Log "Chromium exited with code 127 … libnss3.so".** Builder's preview-image job after each publish; the Pilot image lacks Chromium libraries. Pages are unaffected.
