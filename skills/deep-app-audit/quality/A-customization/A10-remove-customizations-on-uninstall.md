---
id: A10
area: customization
mechanism: M02
---
# A10 — Remove the app's Custom Fields and Property Setters on uninstall

**Why:** An uninstall that leaves fields and property setters behind leaves the site in the
broken state the uninstall was meant to fix. The fields stay on every form, the property
setters keep changing standard behaviour, and no app owns them any more.

## Bad

```python
# my_app/hooks.py
after_install = "my_app.setup.install.after_install"
```

## Good

```python
# my_app/hooks.py
after_install = "my_app.setup.install.after_install"
after_migrate = "my_app.setup.install.after_install"
before_uninstall = "my_app.setup.uninstall.before_uninstall"
```

```python
# my_app/setup/uninstall.py
import frappe

from my_app.setup.install import CUSTOM_FIELDS


def before_uninstall():
	for doctype, fields in CUSTOM_FIELDS.items():
		for field in fields:
			frappe.db.delete("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]})

	frappe.db.delete("Property Setter", {"module": "MyApp"})
	frappe.clear_cache()
```

## Find

- `rg -n 'create_custom_fields|make_property_setter' --type py` returns hits and
  `rg -n 'before_uninstall|after_uninstall' hooks.py` returns nothing.
- An uninstall hook that deletes the app's own DocTypes but not its Custom Fields.

## Confirm

`remove_app` runs `before_uninstall`, `before_app_uninstall`, `after_uninstall`, and
`after_app_uninstall` (`frappe/installer.py:remove_app`). All four exist on develop.

Removing the app's own DocTypes is automatic. Custom Fields and Property Setters on another
app's DocTypes are not, because they are rows in that app's tables.

A `before_disable` hook that marks the app's customizations `is_app_disabled` is a different
mechanism and does not replace this rule. Disable hides the fields. Uninstall must delete them.

The default print format Property Setter from A31 is part of the same cleanup.
