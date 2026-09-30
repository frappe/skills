---
id: A40
area: customization
mechanism: M42
---
# A40 — Ship a report, print format, or web form as a standard file in the app

**Why:** A non-standard report runs its script through `safe_exec`, so it cannot import the app's
own modules and cannot be tested. Nothing in the app tree records what it does. The record is also
lost or overwritten by a fixture sync, and the failure appears as a broken report with no history.

## Bad

The app ships `fixtures/report.json` with a Report record whose `is_standard` is `No` and whose
logic lives in the `report_script` field.

## Good

```
my_app/my_app/report/permit_summary/
	permit_summary.json     "is_standard": "Yes", "report_type": "Script Report"
	permit_summary.py       def execute(filters=None)
	permit_summary.js       frappe.query_reports["Permit Summary"] = { filters: [...] }
```

```python
# my_app/my_app/report/permit_summary/permit_summary.py
import frappe


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)
```

## Find

- `rg -n '"Report"|"Print Format"|"Web Form"|"Dashboard Chart"|"Notification"' hooks.py` inside
  `fixtures`.
- `rg -n '"is_standard":\s*"No"' --glob '**/*.json'` in the app.
- `rg -n 'report_script' --glob '**/*.json'`.
- A Report or Print Format JSON in the app tree with no sibling `.py` or `.html`.

## Confirm

A standard Script Report loads the module and calls `execute`, `execute_snapshot_report`, or
`get_xlsx_styles` only (`frappe/core/doctype/report/report.py`). A non-standard report runs
`report_script` under `safe_exec`, with the Script API and nothing else.

The JSON for a standard report, print format, web form, or DocType Layout is written only in
developer mode. An app that ships one must keep the generated file in version control.

`is_standard` on a site-created record is correct when the site owns it. The finding is an app that
ships a non-standard record.

A Query Report with SQL in the record has the same problem plus the schema coupling in A37.
