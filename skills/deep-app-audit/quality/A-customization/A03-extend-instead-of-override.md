---
id: A03
area: customization
mechanism: M14
semgrep: {rules: [override-doctype-class], coverage: partial}
---
# A03 — Use `extend_doctype_class` when the app only adds behaviour

**Why:** `override_doctype_class` takes the last app's class and drops every other app's
override. An app that only adds methods takes the whole DocType away from every other app for
no gain.

## Bad

```python
# my_app/hooks.py
override_doctype_class = {"Contact": "my_app.overrides.contact.CustomContact"}
```

```python
# my_app/overrides/contact.py
from frappe.contacts.doctype.contact.contact import Contact


class CustomContact(Contact):
	def get_crm_owner(self):
		return frappe.db.get_value("Customer", self.company_name, "account_manager")
```

## Good

```python
# my_app/hooks.py
extend_doctype_class = {"Contact": "my_app.overrides.contact.ContactCRMMixin"}
```

```python
# my_app/overrides/contact.py
class ContactCRMMixin:
	def get_crm_owner(self):
		return frappe.db.get_value("Customer", self.company_name, "account_manager")
```

## Find

- `rg -n 'override_doctype_class' hooks.py`.
- For each entry, check whether any method in the override class also exists on the base class.
- An override class with no shadowed method and no `super()` call is the shape this rule covers.

## Confirm

An override that changes a lifecycle method is not a finding. It needs
`override_doctype_class`, because a mixin cannot control the method resolution order against
the controller.

`extend_doctype_class` puts the extension classes before the base class in the MRO, in reverse
app order (`frappe/model/base_document.py:_create_extended_class`). An extension that defines
a method the controller also defines does shadow it, and then the same `super()` rule as A02
applies.

Two apps may extend one DocType at the same time. When both define the same method name, the
order between them is the app order. Treat a shared method name across two extensions as a
finding.
