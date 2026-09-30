---
id: A16
area: customization
mechanism: M18
---
# A16 — Give every Custom Field a name that no other app can choose

**Why:** Two apps that add `permit_no` to Sales Invoice cannot be installed together. The second
install fails, or one app silently reads the other app's data. A prefix removes the whole class
of failure.

## Bad

```python
CUSTOM_FIELDS = {
	"Sales Invoice": [
		{"fieldname": "permit_no", "label": "Permit No", "fieldtype": "Data", "insert_after": "customer"},
		{"fieldname": "status", "label": "Permit Status", "fieldtype": "Select", "insert_after": "permit_no"},
	]
}
```

## Good

```python
CUSTOM_FIELDS = {
	"Sales Invoice": [
		{
			"fieldname": "myapp_permit_no",
			"label": "Permit No",
			"fieldtype": "Data",
			"insert_after": "customer",
		},
		{
			"fieldname": "myapp_permit_status",
			"label": "Permit Status",
			"fieldtype": "Select",
			"options": "\nPending\nGranted",
			"insert_after": "myapp_permit_no",
		},
	]
}
```

## Find

- Collect every `fieldname` in the app's `create_custom_fields` dicts and in
  `fixtures/custom_field.json`.
- Flag any fieldname with no app-specific prefix.
- Compare each fieldname against `frappe.get_meta(dt).get_field(fieldname)` for the standard
  DocType.
- Compare the set against the Custom Fields of every other app on the bench.
- Check every `fetch_from` value: the source path must name a Link field on the same DocType and
  a field that exists on its target.

## Confirm

`CustomField.validate` rejects a duplicate fieldname on the same DocType and runs
`check_fieldname_conflicts`, so a collision with a standard field fails at install. A collision
with another app's Custom Field fails only when both are installed, which is why the audit must
look across the bench.

A short generic name such as `status`, `type`, `amount`, `remarks`, or `reference` is a strong
finding even with no collision today.

A `fetch_from` that names a removed field blocks every save of the DocType. Resolve each one.

A mandatory Custom Field with no default and no writer blocks every non-desk creation path. See
A18.
