---
id: M13
---
# M13 — `override_doctype_class`

**What:** `override_doctype_class` in `hooks.py` maps a DocType name to a dotted path to a
class. `import_controller` loads the original controller, then replaces it with the class from
the hook. From then on every document of that DocType in that site is an instance of the
override, wherever it is loaded from. It is the strongest customization the framework offers for
a DocType another app owns.

**Guards:** The override must be a subclass of the original controller, else the framework
throws `Invalid Override`. Only the last entry is used: `class_overrides[doctype][-1]`. Two apps
that both override the same DocType do not both take effect. `install_app` prints a warning when
the app being installed overrides a DocType another app already overrides, and `bench migrate`
prints the same warning for every DocType with more than one override. Neither stops the install
or the migrate. The resulting class is cached per site.

## Good use

Reach for an override only when the app must change what a core method does. When the app only
adds behaviour, use `extend_doctype_class` (M14) or `doc_events` (M12); both compose with other
apps, and an override does not.

For an ERPNext behaviour that differs by country or tax regime, use `regional_overrides` first.
It replaces one method for one region and leaves the class to everyone else.

Subclass the original and call `super()` in every method you define.

```python
# my_app/hooks.py
override_doctype_class = {"Sales Invoice": "my_app.overrides.sales_invoice.CustomSalesInvoice"}
```

```python
# my_app/overrides/sales_invoice.py
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class CustomSalesInvoice(SalesInvoice):
    def validate(self):
        super().validate()
        self.validate_permit_number()
```

Import the original from its own module, not from `frappe.get_controller`. Calling
`get_controller` at import time inside the override module builds a cycle: the framework is in
the middle of building that class.

Keep the override thin. Every method the override defines is a method the app must keep in step
with core for the life of the app. A method that does not call `super()` silently drops the core
step it replaced, and a later core fix never reaches the site.

Document that the app takes the DocType. A site cannot install two apps that override the same
DocType and get both behaviours, and the framework only warns.

## Rules

- A02 — An overriding controller subclasses the original and calls `super()`
- A04 — Use `regional_overrides` before a controller override
- A03 — Use `extend_doctype_class` when the app only adds behaviour
