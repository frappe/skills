---
id: M17
---
# M17 — `override_whitelisted_methods`

**What:** `override_whitelisted_methods` maps the dotted path of a whitelisted method to the
dotted path of a replacement. `frappe.override_whitelisted_method` returns the last override for
a path, or the path itself when there is none. It lets an app change what an existing API
endpoint does, without patching the module that defines it.

**Guards:** The override is consulted at a small number of dispatch points only: `execute_cmd`
for `/api/method`, the v2 API, the API discovery listing, the desk treeview loader, and the
document mapper (`get_mapped_doc` and `map_docs`). Every other caller is unaffected. Python code
that imports the original function and calls it runs the original. A `frappe.call` from
JavaScript goes through `execute_cmd` and is redirected; a call from a controller is not. Only
the last override wins, so two apps that override the same path do not compose. The replacement
must itself be whitelisted: the dispatch points call `frappe.is_whitelisted` on the resolved
method.

## Good use

Use the override when the app must change the answer an existing endpoint gives to the desk or
to an external caller, and the app cannot change the caller.

```python
# my_app/hooks.py
override_whitelisted_methods = {
    "erpnext.stock.get_item_details.get_item_details": "my_app.stock.get_item_details",
}
```

Keep the signature and the return shape of the original. The caller is core JavaScript or an
external client that the app does not control, and neither was changed. A replacement that takes
different parameters or returns a different shape breaks the caller at run time only.

Call the original from the replacement and adjust the result. This keeps the app's change small
and lets core changes reach the site.

```python
# my_app/stock.py
import frappe
from erpnext.stock.get_item_details import get_item_details as _get_item_details


@frappe.whitelist()
def get_item_details(args, doc=None, for_validate=False, overwrite_warehouse=True):
    out = _get_item_details(args, doc, for_validate, overwrite_warehouse)
    out["my_app_permit_required"] = _permit_required(out)
    return out
```

Do not use the override to enforce a rule. Python callers reach the original, so the rule holds
for RPC only. A rule that must always hold belongs in the document lifecycle.

Also use the mapper path deliberately. Overriding a `get_mapped_doc` entry point changes what
the "Create" buttons produce, and the override is read by `map_docs` as well.

## Rules

- A05 — An overridden whitelisted method keeps the signature and only changes RPC callers
- A38 — Every `frappe.call` target resolves to a whitelisted method that still exists
- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve
