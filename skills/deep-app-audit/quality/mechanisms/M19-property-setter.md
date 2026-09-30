---
id: M19
---
# M19 — Property Setter

**What:** A Property Setter record changes one property of a DocType, a DocField, a DocType
Link, a DocType Action, or a DocType State, without changing the JSON that ships with the app
that owns it. `Meta.apply_property_setters` reads every Property Setter for the DocType and
applies it by `doctype_or_field`: a `DocType` row sets a property on the meta itself, a
`DocField` row sets a property on the matching field, and the other three set a property on the
matching row by `name`.

**Guards:** The name of the record is `<doctype>-<field or row or main>-<property>`, so one
property of one target has one record; saving a new one deletes the previous one for the same
target. The fieldtype of `naming_series` cannot be changed. `on_update` runs
`validate_fields_for_doctype` when the record carries the `validate_fields_for_doctype` flag,
which `make_property_setter` sets by default and which `frappe.flags.in_patch` clears. The meta
layer hides a Property Setter whose `is_app_disabled` flag is set and one whose module is
disabled.

## Good use

Use `frappe.make_property_setter` from install code, so the change is in version control and
lands on every site the app installs on.

```python
# my_app/setup/install.py
import frappe


def after_install():
    frappe.make_property_setter(
        {
            "doctype": "Sales Invoice",
            "fieldname": "po_no",
            "property": "reqd",
            "value": 1,
            "property_type": "Check",
        },
        is_system_generated=True,
        module="My App",
    )
```

Set the app's own print format as the default with a Property Setter on the DocType, so users
get it without changing a setting on each site.

Before you make a standard field mandatory, find every writer. A desk user fills the field. A
background job, a REST caller, a data import, and another app's controller do not, and each of
them starts to fail on a rule they never saw.

Never unset `reqd` or `read_only` on a standard field. Core reads a mandatory field without
checking whether it is filled, and a read-only field is read-only because core owns its value.
Customize Form refuses both changes; a Property Setter written directly does not, and the
failure appears later, in core code, on a value core assumed was there.

Remove the app's Property Setters on uninstall, together with its Custom Fields.

Set the `module` field, so the enable and disable hooks and the module filter can hide the
change with the rest of the app.

## Rules

- A17 — Do not unset `reqd` or `read_only` on a standard field
- A18 — Before you make a standard field mandatory or hidden, find every writer
- A31 — Set the app's print format as the default with a Property Setter on install
- A10 — Remove the app's Custom Fields and Property Setters on uninstall
