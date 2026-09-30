---
id: M18
---
# M18 — Custom Field

**What:** A Custom Field record adds a field to any DocType, standard or custom. `Meta` reads
every Custom Field for the DocType, orders them by `idx`, marks them `is_custom_field`, and
appends them to the field list. A Custom Field that is not virtual is a real column, added by
`updatedb` when the record is saved. This is the normal way an app adds data to a DocType
another app owns.

**Guards:** `validate` refuses a new field whose fieldname already exists on the DocType,
refuses an empty fieldname, and refuses a fieldtype change outside the groups in
`ALLOWED_FIELDTYPE_CHANGE`. It also runs `check_fieldname_conflicts`, which catches a fieldname
that collides with a controller method or a framework attribute. `on_update` runs
`validate_fields_for_doctype` and `frappe.db.updatedb` unless `ignore_validate` or
`frappe.flags.in_create_custom_fields` is set. A system-generated field cannot be renamed. A
field owned by Administrator can only be deleted by Administrator. Deleting a Custom Field also
deletes the Property Setters for that fieldname. The meta layer hides a Custom Field whose
`is_app_disabled` flag is set, whose module is disabled, or whose Link or Table target belongs
to a disabled app.

## Good use

Create the fields the app's own code reads in code, on install, with `create_custom_fields`. The
helper sets `is_system_generated` and the module, so the site can see which app owns the field
and the enable and disable hooks can hide it.

```python
# my_app/setup/install.py
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
    "Sales Invoice": [
        {
            "fieldname": "my_app_permit_no",
            "label": "Permit No",
            "fieldtype": "Data",
            "insert_after": "customer",
            "module": "My App",
        }
    ]
}


def after_install():
    create_custom_fields(CUSTOM_FIELDS)
```

Prefix every fieldname with the app. Two apps that both add `permit_no` to Sales Invoice cannot
be installed on the same site, and the second install fails on a name that already exists.

Remove the fields on uninstall, in `before_uninstall`. A column that no app owns stays on the
table for the life of the site.

Count the columns. Every non-virtual Custom Field is a column, and MariaDB limits the bytes in
one row. An app that adds many Data and Text fields to a DocType that other apps also extend can
push the row over the limit, and the failure hits `bench migrate` on a site that is already
live.

Index a Custom Field that a filter, a report, or a join uses. Add the index in code, from a
patch, not by hand on one site.

Set `insert_after` to a field the app can rely on. A missing `insert_after` value puts the field
at the end of the form, which is confusing but harmless; pointing at another app's field ties
the layout to that app.

Do not ship Custom Fields as fixtures. A fixture is force-imported on every migrate, carries no
ownership mark, and overwrites what the site changed.

## Rules

- A08 — Create the Custom Fields the app's logic reads in code, not as fixtures
- A16 — Give every Custom Field a name that no other app can choose
- A19 — Keep the added columns inside the database row size limit
- A10 — Remove the app's Custom Fields and Property Setters on uninstall
- A18 — Before you make a standard field mandatory or hidden, find every writer
- A09 — A fixture is force-imported on every migrate. Export only records the app owns
