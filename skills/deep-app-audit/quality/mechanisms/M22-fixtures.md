---
id: M22
---
# M22 — Fixtures

**What:** The `fixtures` hook names doctypes, with optional filters, that `bench export-fixtures`
writes as JSON files into `<app>/fixtures/`. `sync_fixtures` imports every file in that folder
on install and on migrate.

**Guards:** The import runs with `force=True` and `reset_permissions=True`, so a record in a file
overwrites the record on the site, field by field. The import commits after every file, so a
failure in a later file leaves the earlier files applied. Files are imported in sorted filename
order, and `fixture_auto_order` adds a zero-padded number prefix so the order of the `fixtures`
hook survives as the filename order. `DocType` and `Page` are refused at export with a message
and a non-zero exit. A JavaScript file under `fixtures/custom_scripts` is refused at import with
a message. An import that raises `ImportError` or `DoesNotExistError` is skipped and the migrate
continues.

## Good use

A fixture is for a record that the app owns and that the site must not change: a Role, a UOM, a
Print Format, a Custom Role, a Workflow the app defines. The app is the only writer. The site
reads the record and links to it.

Filter the export so the file holds the app's own records only. Without a filter, the export
takes every record of the doctype on the developer's site, which puts that site's data into the
app and then pushes it onto every other site at the next migrate.

```python
fixtures = [
    {"doctype": "Role", "filters": {"role_name": ["like", "Fleet %"]}},
    {"doctype": "Custom Role", "filters": {"report": ["like", "Fleet %"]}},
]
```

Order the files when one fixture links to another. A Workflow needs its Workflow State rows
first. Set `fixture_auto_order = True` so the export numbers the filenames in the order of the
`fixtures` hook, instead of relying on the alphabetical order of the doctype names.

A record that the site is meant to edit is not a fixture. Seed it once from `after_install`, so
the site keeps its edit. A Custom Field that the app's own code reads is not a fixture either:
create it in code, so an uninstall can remove it and a site edit cannot delete it silently.

## Rules

- A08 — Create the Custom Fields the app's logic reads in code, not as fixtures
- A09 — A fixture is force-imported on every migrate. Export only records the app owns
- A40 — Ship a report, print format, or web form as a standard file in the app
