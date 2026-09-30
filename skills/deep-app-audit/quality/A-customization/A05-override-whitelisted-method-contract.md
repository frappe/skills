---
id: A05
area: customization
mechanism: M17
---
# A05 — An overridden whitelisted method keeps the signature and only changes RPC callers

**Why:** `override_whitelisted_methods` is read at RPC dispatch only. Python code that imports
the original function still calls the original. An app that expects the override to apply
everywhere ships behaviour that runs for the desk and not for a background job.

## Bad

```python
# my_app/hooks.py
override_whitelisted_methods = {
	"frappe.client.get_list": "my_app.api.get_list"
}
```

```python
# my_app/api.py
@frappe.whitelist()
def get_list(doctype, filters=None):
	"""Missing fields, order_by, limit_start, limit_page_length, parent, debug."""
	return frappe.get_list(doctype, filters=filters)
```

## Good

```python
# my_app/api.py
import frappe
from frappe.client import get_list as core_get_list


@frappe.whitelist()
def get_list(doctype, *args, **kwargs):
	if doctype == "Project Task":
		frappe.only_for("Projects Manager")
	return core_get_list(doctype, *args, **kwargs)
```

## Find

- `rg -n 'override_whitelisted_methods' hooks.py`.
- For each entry, read the original function signature and the override signature.
- An override with fewer parameters, or with no `**kwargs`, is a finding.
- `rg -n '<original dotted path>' --type py` across the bench. Every direct import is a caller
  the override does not reach.

## Confirm

`override_whitelisted_method` returns the last override (`frappe/__init__.py`). Two apps that
override the same path is a finding on its own: only the last installed app takes effect.

The override applies at `frappe/handler.py` RPC dispatch, the v2 API, discovery, the treeview,
and the document mapper. Nothing else consults it.

An override that adds a keyword argument with a default is not a finding. An override that
removes a parameter, renames one, or changes the order is a finding, because core passes those
names from the request.
