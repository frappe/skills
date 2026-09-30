---
id: M42
---
# M42 — Report code

**What:** A Report record with `is_standard = "Yes"` loads a module from the app tree. Frappe
calls `execute`, `execute_snapshot_report` or `get_xlsx_styles` in that module, and nothing
else. The sibling `<report>.js` sets `frappe.query_reports["<Report Name>"]` with filters and
formatters. The sibling `<report>.html` is the print template. A Report record with
`is_standard = "No"` holds its Python in the `report_script` field, and that code runs under
`safe_exec`.

**Guards:** The method allowlist in `Report.execute_script_report` refuses any other name. A
non-standard report has the Script API only: it cannot import the app's modules, and it cannot
be tested. The JSON of a standard report is written only in developer mode, so the file in the
app tree is the record. A Query Report holds SQL in the record and couples the report to the
table names.

## Good use

The app ships the report as a directory with the JSON, the Python and the JavaScript together.

```
my_app/my_app/report/permit_summary/
	permit_summary.json
	permit_summary.py
	permit_summary.js
```

`execute(filters=None)` returns columns and rows. It reads the filters, it makes one query per
data set, and it bounds the rows. Aggregation belongs in the query, not in a Python loop over
every row. The function is importable, so a test calls it directly with a filter dict.

The client file registers the filters and the cell formatter:

```javascript
frappe.query_reports["Permit Summary"] = {
	filters: [{ fieldname: "company", fieldtype: "Link", options: "Company", reqd: 1 }],
};
```

A required filter keeps the report from running with no bound at all.

The report reads the DocTypes through the query builder or `frappe.get_all`. Raw SQL against a
core table couples the app to a schema the framework owns and changes without notice.

## Rules

- A40 — Ship a report, print format, or web form as a standard file in the app.
- A37 — Do not name a core table in raw SQL.
- B38 — Keep SQL portable, or branch on the database type.
