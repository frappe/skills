---
id: A18
area: customization
mechanism: M19
---
# A18 — Before you make a standard field mandatory or hidden, find every writer

**Why:** A desk user fills the field. A background job, a REST caller, a mobile client, an
inbound email, and an auto-created document do not. A mandatory Property Setter breaks each of
those paths, and the failure appears far from the change.

## Bad

```python
# my_app/setup/install.py
def after_install():
	make_property_setter("Issue", "customer", "reqd", 1, "Check")
```

Tickets created from inbound email have no customer. Every inbound mail now fails.

## Good

```python
# my_app/hooks.py
doc_events = {"Issue": {"validate": "my_app.support.require_customer"}}
```

```python
# my_app/support.py
import frappe
from frappe import _


def require_customer(doc, method=None):
	"""Ask a desk user for the customer. Let the mail handler fill it later."""
	if doc.get("via_customer_portal") or frappe.flags.in_email_queue:
		return
	if not doc.customer:
		frappe.throw(_("Customer is required on a ticket raised in the desk."))
```

## Find

- Property Setter records or `make_property_setter` calls with `property` in `reqd`, `hidden`,
  `read_only`, `default`, `precision`, or `options`, on a DocType the app does not own.
- For each hit, find the server-side writers:
  `rg -n 'frappe\.(get_doc|new_doc)\(\s*\{?\s*["\x27]<doctype>' --type py` across every app.
- `rg -n '"doctype":\s*"<doctype>"' --type py` for dict-built documents.
- Check the DocType for an email inbox, a web form, a portal page, and an API consumer.

## Confirm

A field that becomes mandatory is a finding when any writer outside the desk form creates the
document. List those writers before you accept or reject.

A field moved to another tab with `hidden` set has the same effect as mandatory plus hidden: the
mandatory check still runs and the user cannot see the field. That combination is always a
finding.

A `precision` change on an amount field changes rounding for every document. Check that debit and
credit still balance under the new precision.

A change on a DocType the app itself ships is not a finding for this rule. The app owns every
writer.
