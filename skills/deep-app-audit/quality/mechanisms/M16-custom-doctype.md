---
id: M16
---
# M16 — Custom DocType

**What:** A DocType created from the desk has `custom=1`. It is a database row, not a file in an
app. A site owner uses it to add a DocType without writing code, and an app that ships a
`fixtures` entry for DocType cannot: fixtures refuse the DocType DocType.

**Guards:** `import_controller` never loads a file for a custom DocType. It returns `NestedSet`
when `is_tree` is set and `Document` otherwise, so a controller file for it is never imported.
The desk skips `add_code` and `add_html_templates`, so `<doctype>.js`, `<doctype>_list.js`,
`<doctype>.css`, and the HTML templates in the DocType folder are not loaded. The portal list
renderer returns `False` for a custom DocType, so it has no portal list page. The
`override_doctype_dashboards` hook is skipped for it.

## Good use

Use a Custom DocType for data a site needs that no app models: a lookup table, a per-site
register, a small master. It is the right tool when the site owner owns the data and no code has
to run.

Give the DocType logic in the ways the framework does read for a custom DocType:

- A Client Script record for form behaviour. The desk loads Client Scripts for a custom DocType.
- A Server Script record of type DocType Event for a server-side rule, on a site where server
  scripts are enabled.
- A `doc_events` entry in an app, which works for any DocType name, custom or not.

When the rule must always hold, put it on the server. A Client Script runs in the desk form
only, so the REST API, a background job, and a data import all bypass it.

When an app needs the DocType, ship the DocType as a standard DocType in the app instead. A
standard DocType lives in version control, has a controller, has tests, and migrates with the
app. Converting a Custom DocType into a standard one later means exporting the JSON, clearing
`custom`, and shipping a patch.

Do not ship a controller file, a form script file, or a `<doctype>_dashboard.py` for a DocType
with `custom=1`. None of them is loaded, so the code looks live and is not.

## Rules

- A30 — Do not ship code for a DocType created with `custom=1`
- A07 — Reuse the DocType the stack already models
- A20 — A rule that must always hold does not live in a Client Script
- A22 — Ship an app's logic as app code, not as a Server Script record
