---
name: builder-docs-site
description: Publish a GitHub Markdown docs repo (VitePress-style handbook) as a Frappe Builder site, optionally on a new Frappe Cloud v2 VM created through dashboard.frappe.io (Central) and Pilot. Use to recreate or mirror a docs site in Builder, or to provision a Cloud v2 server with a Builder site.
---

# Builder docs site

The result is Builder-native and holds no copy of the docs:

- One **Doc Page** component renders every page on the server. Its data script reads the route, fetches the Markdown from the repo through jsDelivr, renders it with `frappe.utils.md_to_html`, and feeds the outline, prev/next and sidebar state to bindings, repeaters and visibility conditions.
- Five dynamic-route **shells** (`<prefix>/:p1` … `<prefix>/:p1/:p2/:p3/:p4/:p5`) embed it, because a Builder route variable matches one path segment. Plus `home` (hero blocks + home Markdown) and `api-reference/:name` (Scalar).
- Colours are **Builder Tokens** with dark values; the theme switch sets Builder's `data-theme`. The editor canvas shows the same page as the live route.

`examples/atlas.json` is the spec that built https://atlas-docs.mumbai.frappe.cloud from `frappe/atlas`.

## Setup

```sh
SKILL=<this skill's directory>/scripts
python3 -m venv ~/.cache/builder-docs-site/venv
PY=~/.cache/builder-docs-site/venv/bin/python
$PY -m pip install -r $SKILL/requirements.txt
ls ~/.cache/ms-playwright/chromium-* >/dev/null 2>&1 || $PY -m playwright install chromium
```

Run every script from one working directory: state (sessions, keys) lives in `./.cloudv2`. Spec extraction needs Node 22.6+. `build.py` lints with the `frappe-builder` skill's linter, taken from a sibling `frappe-builder` skill or downloaded from frappe/builder once.

## Steps

### 1. Provision

Skip when a Builder site with server scripts enabled already exists and you hold an Administrator API key (`FRAPPE_API_KEY` / `FRAPPE_API_SECRET`). Details and failure modes: [reference/cloud-v2.md](reference/cloud-v2.md).

```sh
$PY $SKILL/cloud.py login EMAIL                 # Central emails a 6-digit code
$PY $SKILL/cloud.py login EMAIL --code CODE
$PY $SKILL/cloud.py teams
$PY $SKILL/cloud.py options --team TEAM         # region, image, plans with prices, billing profile
$PY $SKILL/cloud.py create --team TEAM --title "Docs" --plan vm-1
$PY $SKILL/cloud.py bench --server SERVER
$PY $SKILL/cloud.py site --server SERVER --name NAME.REGION.frappe.cloud
$PY $SKILL/cloud.py builder --server SERVER --site SITE      # ~10 minutes
$PY $SKILL/cloud.py site-key --server SERVER --site SITE
```

- Get the code with AskUserQuestion (the user types it under "Other"); a private secret card never hands the value back.
- A VM is billable: confirm the team, plan and monthly price from `options` with the user before `create`. An incomplete billing profile blocks creation; the team owner fills it at dashboard.frappe.io → Billing → Add billing details. No card unless `options` says a payment method is required.

Done when `site-key` saved `.cloudv2/SITE.json` and `https://SITE/api/method/ping` answers `pong`.

### 2. Spec

```sh
git clone --depth 1 -b BRANCH https://github.com/OWNER/REPO repo
$PY $SKILL/spec_from_vitepress.py repo --repository OWNER/REPO --branch BRANCH \
    --site https://SITE [--published https://OWNER.github.io/REPO/] > spec.json
```

Then fill what the extractor cannot read: `source_links.directories` (code folders whose links should open on GitHub), `home.css` for classes in the home Markdown's raw HTML, and `preview_route`. A repo without VitePress: write the spec by hand from `examples/atlas.json`.

Done when the spec has a title, nav, at least one sidebar, the home source, brand colours, and every API reference `spec` answers 200 (repo path through jsDelivr, or an `https://` URL).

### 3. Dry run

```sh
$PY $SKILL/build.py spec.json --emit out
$PY $SKILL/sandbox.py out/doc-page.data_script.py --block out/doc-page.json --route /PREFIX/LEAF/PAGE
$PY $SKILL/sandbox.py out/page-home.data_script.py --page
$PY $SKILL/sandbox.py out/page-api-reference_name.data_script.py --page --form name=FIRST_API
```

Run the doc page script for a leaf page, a directory index, a file outside the docs folder, and a missing page.

Done when every real page prints a title, an outline and `not_found: False`, the missing one prints `not_found: True`, and the build printed no lint error.

### 4. Build

```sh
$PY $SKILL/build.py spec.json [--clean-routes]
```

Ask the user to close editor tabs on these pages first: an open tab saves its old tree over yours. Pass `--clean-routes` when static pages already exist under the prefix, because a static route beats every dynamic shell. Re-running is safe: tokens are matched by label, components and pages updated in place.

Done when it printed both components and every page with no lint error.

### 5. Verify

```sh
$PY $SKILL/verify.py spec.json --editor "$($PY $SKILL/cloud.py login-url --server SERVER --site SITE)"
```

Then open every screenshot in `shots/` and compare it with the original site.

Done when it reports 0 failing checks, and the screenshots show the tokens applied (sidebar fill, brand-coloured active link and nav item), `dark.png` dark, the drawer open in `mobile-drawer.png`, and the rendered page inside the canvas in `editor.png`.

## Changing the templates or build.py

Read [reference/traps.md](reference/traps.md) first: each entry is a failure this design already routes around, with its symptom. Keep the sandbox and the lint gate in the loop: `--emit`, `sandbox.py`, then build.

## What the user should know

- Content comes through jsDelivr, which caches a branch for up to 12 hours; search indexes raw GitHub and is fresher.
- A new page in the repo renders at its URL at once; it joins the sidebar when the spec (or the Doc Page sidebar in the editor) gets an entry.
- `<title>` is set in the browser: a component data script cannot set it.
- The site needs server scripts enabled (`md_to_html`); Pilot benches enable them.
