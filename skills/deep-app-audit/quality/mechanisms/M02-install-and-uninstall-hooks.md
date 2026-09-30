---
id: M02
---
# M02 — Install and uninstall hooks

**What:** `install_app` and `remove_app` call named hooks so an app can seed data, create roles,
add its Custom Fields, and remove them again. The install order is `required_apps`, then
`before_install` of the app, then `before_app_install` of every app, then the schema sync, then
`after_install`, then `after_app_install`, then `sync_jobs`, `sync_fixtures`,
`sync_customizations`, `sync_dashboards`, and last `after_sync`. The uninstall order is
`before_uninstall`, `before_app_uninstall`, the module and doctype deletion, then
`after_uninstall` and `after_app_uninstall`.

**Guards:** A `before_install` hook that returns `False` stops the install, and `install_app`
returns without a message. `before_install` runs before `sync_for`, so the app's own DocTypes do
not exist yet. `before_app_install` and `after_app_install` receive the name of the app being
installed, so a handler must accept that argument. `required_apps` are installed first, but only
for a `bench install-app`; a bare site with a missing dependency still fails at import time.

## Good use

Split the work by what exists at each step.

`before_install` sees the site as it is before this app touched it. Use it to check a
precondition, such as a required app or a minimum framework version. Return nothing.

`after_install` runs after the app's DocTypes are synced and the app is in
`installed_apps`. This is where the app creates its records: Custom Fields, roles, default
settings, and any master data the app owns.

```python
# my_app/setup/install.py
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    create_custom_fields(
        {
            "Sales Invoice": [
                {
                    "fieldname": "my_app_permit_no",
                    "label": "Permit No",
                    "fieldtype": "Data",
                    "insert_after": "customer",
                }
            ]
        }
    )
```

`after_sync` runs last, after fixtures and customizations are imported. Use it for work that
needs a fixture record to be present.

`before_app_install` and `after_app_install` let an app react to another app. Write the handler
with an `app_name` parameter and return early for every app the handler does not own.

Make the uninstall the mirror of the install. `before_uninstall` deletes the Custom Fields and
Property Setters the app created, so the site keeps no column and no property change that no app
owns. Delete by fieldname and DocType, not by a range, because another app may have added
fields to the same DocType.

Every install hook runs with `frappe.flags.in_install` set. Notifications, Webhooks, and Server
Scripts are muted under that flag, so install code must do its own work and must not expect a
data-driven event to fire.

## Rules

- A10 — Remove the app's Custom Fields and Property Setters on uninstall
- A11 — Declare hard dependencies in `required_apps`. Guard optional ones
- A39 — A `before_install` hook must not return a value
- A08 — Create the Custom Fields the app's logic reads in code, not as fixtures
- A13 — Every module the app imports at load must be declared and present
- A23 — Install, migrate, and patch code cannot rely on Notifications, Webhooks, or Server Scripts
- A31 — Set the app's print format as the default with a Property Setter on install
