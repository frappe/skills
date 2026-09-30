---
id: M03
---
# M03 — Enable and disable hooks

**What:** A site can turn an installed app off without dropping its schema or its data.
`disable_app` runs `before_disable`, sets the app to disabled, then runs `after_disable`.
`enable_app` runs `before_enable`, clears the flag, then runs `after_enable`. A disabled app is
not in `get_active_apps`, so its hooks leave the merged hook dict and its assets stop loading.

**Guards:** Both functions hold a file lock, run in one transaction, and commit at the end. A
failure rolls the whole toggle back. `disable_app` refuses when another active app declares the
app in `required_apps`, and `enable_app` refuses when a dependency is still disabled. The app
`frappe` cannot be disabled. The meta layer hides a Custom Field or a Property Setter whose
`is_app_disabled` flag is set, and it also hides a Link, Table, or Table MultiSelect field whose
target DocType belongs to a disabled app. Scheduled Job Type rows of a disabled app stay in the
table and are skipped at enqueue.

## Good use

The framework removes the app's hooks. It does not remove the records the app wrote into shared
DocTypes. The enable and disable hooks exist so the app can hide and unhide those records.

Set `is_app_disabled` on every Custom Field and Property Setter the app owns in
`before_disable`, and clear it in `after_enable`.

```python
# my_app/setup/app_state.py
import frappe

OWNED = {"dt": ("Sales Invoice", "Delivery Note")}


def before_disable():
    frappe.db.set_value("Custom Field", {"dt": ("in", OWNED["dt"]), "module": "My App"},
                        "is_app_disabled", 1, update_modified=False)


def after_enable():
    frappe.db.set_value("Custom Field", {"dt": ("in", OWNED["dt"]), "module": "My App"},
                        "is_app_disabled", 0, update_modified=False)
```

Set the `module` field on every customization the app creates. The meta layer also hides a
customization whose module is disabled, so a correct `module` value gives the app most of this
behaviour for free.

Keep the hooks small and reversible. The pair runs inside one lock and one transaction, so long
work blocks every other toggle on the site, and a failure halfway leaves nothing behind.

Never drop a table, delete a row, or clear a column in these hooks. A disable is a reversible
state change. Deleting data makes an enable impossible.

## Rules

No rule in the knowledge base covers this mechanism yet.
