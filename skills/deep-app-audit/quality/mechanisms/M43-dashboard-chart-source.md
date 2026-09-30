---
id: M43
---
# M43 — Dashboard Chart Source

**What:** A Dashboard Chart Source lets an app supply the data for a Dashboard Chart of type
`Custom`. The record names a module. The app ships a directory in that module with a Python
file that returns the chart data and a JavaScript file that declares the filters and the chart
configuration under `frappe.dashboards.chart_sources["<Source Name>"]`.

**Guards:** `frappe.dashboards.chart_sources` is a plain object, so the last script that assigns
a key wins. The chart widget reads the registry first and falls back to the server, which reads
the `<source>.js` file from the module directory. The record is exported to files on save and
deleted with its folder on trash, and both actions need developer mode. Chart data is served
through `cache_source`, so the function must be a pure read.

## Good use

The app owns the source and ships it as files.

```
my_app/my_app/dashboard_chart_source/permits_by_month/
	permits_by_month.json
	permits_by_month.js
	permits_by_month.py
```

```javascript
// permits_by_month.js
frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Permits By Month"] = {
	method: "my_app.my_app.dashboard_chart_source.permits_by_month.permits_by_month.get",
	filters: [{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" }],
};
```

The Python function aggregates in the database and returns the labels and the data sets it
needs. A chart runs on a dashboard that several users open at once, so the query is grouped and
bounded in SQL rather than in Python.

The JavaScript file assigns one key, the name of the source the app owns. It does not replace
the whole `frappe.dashboards.chart_sources` object, because that removes every source another
app registered.

## Rules

- A21 — Add to a client-side registry. Do not replace what another app put there.
- A40 — Ship a report, print format, or web form as a standard file in the app.
