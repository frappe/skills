---
id: A09
area: customization
mechanism: M22
---
# A09 — A fixture is force-imported on every migrate. Export only records the app owns

**Why:** Every fixture file is imported with `force=True` and committed on every migrate. A
site edit to any exported record is reverted at the next deploy. When two apps export the same
record, the last app wins and the other app's behaviour disappears.

## Bad

```python
# my_app/hooks.py
fixtures = ["Custom Field", "Property Setter", "Print Format", "Server Script", "Role"]
```

## Good

```python
# my_app/hooks.py
fixtures = [
	{"dt": "Role", "filters": [["role_name", "like", "MyApp %"]]},
	{"dt": "UOM", "filters": [["name", "in", ["Metric Ton", "Cubic Metre"]]]},
]
```

## Find

- `rg -n 'fixtures' hooks.py`. An entry that is a bare string exports every record of that
  DocType on the site.
- `ls fixtures/*.json` and count the records per file.
- Compare the exported record names against the fixture lists of every other app on the bench.
  A name in two apps is a finding.
- `rg -n 'sync_on_migrate' */custom/*.json` for the `custom/` folder form of the same problem.

## Confirm

`import_doc` calls `import_file_by_path(..., force=True, reset_permissions=True)` and commits
per file (`frappe/core/doctype/data_import/data_import.py:import_doc`). The overwrite is
unconditional.

`DocType` and `Page` are refused (`DISALLOWED_FIXTURE_DOCTYPES`). A fixture entry for either is
dead configuration, not a data risk.

`fixtures/custom_scripts/*.js` is refused with a message on develop. An app that still ships
that folder loses those scripts silently.

High-risk DocTypes to flag: `Custom Field`, `Property Setter`, `Server Script`, `Client Script`,
`Print Format`, `Custom DocPerm`, `Workspace`, `Report`, `Notification`. Each is a record a site
administrator also edits.

A filtered fixture that names records with an app-specific prefix is not a finding.
