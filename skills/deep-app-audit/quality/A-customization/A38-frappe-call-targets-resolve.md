---
id: A38
area: customization
---
# A38 — Every `frappe.call` target resolves to a whitelisted method that still exists

**Why:** A method path in JavaScript is a string. Nothing checks it at build time. A renamed
function, a missing decorator, or a method the framework removed produces a runtime error in the
browser, on a button the user pressed, and the server logs show only a permission or a not-found
error.

## Bad

```javascript
frappe.call({
	method: "my_app.api.sync_permit",
	args: { name: frm.doc.name },
	callback(r) {
		frm.reload_doc();
	},
});
```

```python
# my_app/api.py
def sync_permit(name):  # no @frappe.whitelist()
	...
```

## Good

```javascript
frm.call({
	method: "my_app.api.sync_permit",
	args: { name: frm.doc.name },
}).then(() => frm.reload_doc());
```

```python
# my_app/api.py
import frappe


@frappe.whitelist()
def sync_permit(name: str):
	frappe.has_permission("Permit", "write", doc=name, throw=True)
	...
```

## Find

- `rg -no 'method:\s*["\x27][a-zA-Z0-9_.]+["\x27]' --type js` in the app and in Client Script
  records.
- `rg -n 'frappe\.xcall\(|frm\.call\(|frappe\.client\.' --type js`.
- Resolve each path: the module must exist and the function must carry `@frappe.whitelist()`.
- A path whose first segment is not an installed app.
- The same check for every dotted path in `frappe.set_query` and in a link field `query`.

## Confirm

`execute_cmd` resolves the method string, applies `override_whitelisted_methods`, and refuses a
method without the decorator (`frappe/handler.py:execute_cmd`). A missing decorator is certain,
not a candidate.

A path into `frappe.client` or another framework module is valid but couples the app to that
signature. Record it and check it against the target version before an upgrade.

A method name built at run time from a variable cannot be resolved by search. Flag it for reading,
and check that the value comes from the app and never from the request.

A link field `query` path must also carry `@frappe.validate_and_sanitize_search_inputs` and the
signature `(doctype, txt, searchfield, start, page_len, filters)`.
