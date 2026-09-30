---
id: A08
area: customization
mechanism: M18
---
# A08 — Create the Custom Fields the app's logic reads in code, not as fixtures

**Why:** A fixture field carries no ownership mark, so a user deletes it and the app breaks
with no explanation. A fixture also re-imports with `force=True` on every migrate, so it
overwrites the site copy of the field every time. `create_custom_fields` marks the field
system-generated, is idempotent, and can run again after an upgrade.

## Bad

```python
# my_app/hooks.py
fixtures = ["Custom Field"]
```

## Good

```python
# my_app/hooks.py
after_install = "my_app.setup.install.after_install"
after_migrate = "my_app.setup.install.after_install"
```

```python
# my_app/setup/install.py
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Sales Invoice": [
		{
			"fieldname": "myapp_permit_no",
			"label": "Permit No",
			"fieldtype": "Data",
			"insert_after": "customer",
			"read_only": 1,
		}
	]
}


def after_install():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
```

## Find

- `rg -n 'fixtures' hooks.py`, then read the exported list for `"Custom Field"`.
- `ls fixtures/custom_field.json`.
- Cross-check: `rg -n '<fieldname>' --type py` for each exported fieldname. A fieldname the
  app's Python code reads or writes is the case this rule covers.

## Confirm

`create_custom_field` sets `is_system_generated=True` by default
(`frappe/custom/doctype/custom_field/custom_field.py:create_custom_field`). That flag blocks a
rename and hides the field from the Customize Form delete path. It does not stop an
Administrator from deleting the row from the Custom Field list, so the protection is partial.

A Custom Field the app only displays, and never reads in code, is a weak finding. The failure
mode there is a lost label, not a broken code path.

`create_custom_fields` must run from `after_install` and from `after_migrate`. An app that
calls it from `after_install` only never adds a field to a site that installed an earlier
version.

Fixtures stay correct for records the app seeds and the site owns afterwards, such as a Role,
a UOM, or a Stock Entry Type. See A09.
