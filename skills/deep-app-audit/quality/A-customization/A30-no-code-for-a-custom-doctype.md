---
id: A30
area: customization
mechanism: M16
---
# A30 — Do not ship code for a DocType created with `custom=1`

**Why:** A DocType with `custom=1` always gets the plain `Document` class. Its controller file is
never imported, its form script is never loaded, and its dashboard hook is never called. Every
line of that code is dead, and nobody notices until the behaviour is missed in production.

## Bad

The app ships `my_app/doctype/permit_log/permit_log.json` with `"custom": 1`, plus
`permit_log.py` with a `validate` method and `permit_log.js` with a form script.

## Good

```json
{
	"doctype": "DocType",
	"name": "Permit Log",
	"module": "MyApp",
	"custom": 0,
	"is_submittable": 0
}
```

The DocType is a standard DocType of the app's module. The controller and the form script then
load in the normal way.

## Find

- `rg -n '"custom":\s*1' --glob '**/doctype/**/*.json'` in the app.
- For each hit, check the folder for a `.py` file with methods other than the generated stub, and
  for a `.js`, `_list.js`, or `_dashboard.py` file.
- `rg -n 'override_doctype_dashboards' hooks.py` for a Custom DocType key.
- `scheduler_events` or `doc_events` that name a method on a Custom DocType controller.

## Confirm

`import_controller` returns `Document`, or `NestedSet` for a tree, as soon as the DocType row has
`custom` set (`frappe/model/base_document.py:import_controller`). No override and no extension is
consulted.

Desk skips `add_code` and the HTML templates for a custom DocType
(`frappe/desk/form/meta.py`). The portal list renderer returns `False`. The dashboard hook is
skipped.

A Custom DocType created by a site administrator, with no code, is the correct use. The finding is
an app that ships code beside it.

Custom Fields and Property Setters on a Custom DocType work normally. Only code is dropped.
