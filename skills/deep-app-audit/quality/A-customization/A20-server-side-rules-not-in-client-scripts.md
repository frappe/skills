---
id: A20
area: customization
mechanism: M24
---
# A20 — A rule that must always hold does not live in a Client Script

**Why:** A Client Script runs in the desk form only. The REST API, a background job, a data
import, the System Console, and a portal web form all bypass it. A validation that lives only in
a Client Script is not a validation.

## Bad

```javascript
// Client Script on Sales Order, view: Form
frappe.ui.form.on("Sales Order", {
	validate(frm) {
		if (frm.doc.grand_total > 100000 && !frm.doc.custom_approval_ref) {
			frappe.throw(__("Orders above 100,000 need an approval reference."));
		}
	},
});
```

## Good

```python
# my_app/hooks.py
doc_events = {"Sales Order": {"validate": "my_app.sales.require_approval_ref"}}
doctype_js = {"Sales Order": "public/js/sales_order.js"}
```

```python
# my_app/sales.py
import frappe
from frappe import _
from frappe.utils import flt


def require_approval_ref(doc, method=None):
	if flt(doc.grand_total) > 100000 and not doc.custom_approval_ref:
		frappe.throw(_("Orders above {0} need an approval reference.").format(100000))
```

```javascript
// my_app/public/js/sales_order.js — hint only, the server still decides
frappe.ui.form.on("Sales Order", {
	grand_total(frm) {
		frm.toggle_reqd("custom_approval_ref", frm.doc.grand_total > 100000);
	},
});
```

## Find

- `rg -n 'frappe\.throw|frappe\.validated\s*=\s*false|frappe\.msgprint' --type js` in the app and
  in Client Script records, inside a `validate` or `before_save` handler.
- For each, look for a server-side check of the same condition:
  `rg -n '<fieldname>' --type py`.
- An app that ships form behaviour as Client Script fixtures rather than as `doctype_js`.

## Confirm

A Client Script that only improves the form is correct: a filter, a toggle, a fetched display
value, a custom button. The finding needs the script to be the only place a rule holds.

Ask which paths create the document. When the desk form is genuinely the only writer, the
finding is weak. A submittable transaction almost never has one writer.

Logic that must run on many sites belongs in the app as `doctype_js`, not as a Client Script
record. `doctype_js` files load after the owning app's script and before Client Scripts
(`frappe/desk/form/meta.py`).

A Client Script is skipped entirely when the form uses a DocType Layout
(`frappe/public/js/frappe/form/script_manager.js`). A site that adds a layout loses every Client
Script on that DocType with no message.
