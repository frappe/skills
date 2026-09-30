---
id: A19
area: customization
mechanism: M18
---
# A19 — Keep the added columns inside the database row size limit

**Why:** Every Custom Field is a column. MariaDB limits the bytes in one row. An app that adds
many text fields to a busy DocType makes `bench migrate` fail with "row size too large", and the
site cannot be upgraded until fields are removed.

## Bad

```python
CUSTOM_FIELDS = {
	"Sales Invoice": [
		{"fieldname": f"myapp_note_{i}", "label": f"Note {i}", "fieldtype": "Small Text"}
		for i in range(1, 41)
	]
}
```

## Good

```python
# my_app/doctype/sales_invoice_compliance/sales_invoice_compliance.json
# A separate DocType with one row per Sales Invoice, linked by `sales_invoice`.

CUSTOM_FIELDS = {
	"Sales Invoice": [
		{
			"fieldname": "myapp_compliance",
			"label": "Compliance Detail",
			"fieldtype": "Link",
			"options": "Sales Invoice Compliance",
			"insert_after": "customer",
		}
	]
}
```

## Find

- Count the Custom Fields the app adds per DocType. More than about 30 on a standard transaction
  is a candidate.
- Count the `Data`, `Small Text`, `Text`, `Long Text`, and `Text Editor` fields in that set.
  These carry the byte cost.
- On a site: compare the column count of `tab<DocType>` with
  `frappe.get_meta(doctype).get_valid_columns()`.

## Confirm

`get_row_size` estimates the row size for a DocType
(`frappe/database/mariadb/database.py:get_row_size`). The DocType form shows the utilization.
Customize Form catches the row size error on save and points at the field-count article.

A deleted Custom Field leaves its column in the table. `bench trim-tables --dry-run` lists the
columns no DocField claims (`frappe/model/meta.py:trim_tables`). An app that adds and removes
fields across versions raises the row size even when the current field count is small.

Shortening `length` on `Data` fields through Customize Form recovers space and is the cheapest
fix. Moving the fields to a linked DocType is the fix that scales.

This rule is about the schema, not about form usability. A DocType with many fields and no row
size problem is not a finding here.
