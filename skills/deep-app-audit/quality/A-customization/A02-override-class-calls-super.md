---
id: A02
area: customization
mechanism: M13
semgrep: {rules: [override-doctype-class], coverage: partial}
---
# A02 — An overriding controller subclasses the original and calls `super()`

**Why:** A method that does not call the parent drops the core step it replaced. Tax
calculation, stock posting, or status update then stops for every document of that DocType. The
site keeps the bug until support reads the app code.

## Bad

```python
# my_app/overrides/sales_invoice.py
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class CustomSalesInvoice(SalesInvoice):
	def validate(self):
		# Every line of the core validate, pasted and edited.
		self.set_missing_values()
		self.validate_posting_time()
		self.validate_due_date()
		self.check_credit_limit()
```

## Good

```python
# my_app/overrides/sales_invoice.py
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class CustomSalesInvoice(SalesInvoice):
	def validate(self):
		self.validate_project_budget()
		super().validate()
```

## Find

- `rg -n 'override_doctype_class' hooks.py` gives the DocType and the class path.
- In each override class, list the methods that also exist on the base class.
- `rg -n 'super\(\)' <override module>` and compare the two lists.
- A class body longer than about 100 lines is a signal of a copied class.

## Confirm

`import_controller` throws `Invalid Override` when the class is not a subclass of the original
(`frappe/model/base_document.py:import_controller`). A subclass that shadows every method
passes that check, so the framework guard does not cover this rule.

A method that deliberately replaces the parent is a true positive only when the replacement
drops behaviour the core method still needs. Read the core method and list the steps it runs.
When the override repeats those steps, it is a copy and it is a finding.

`before_validate` and `validate` on a plain `Document` subclass have no parent body. A missing
`super()` call there is not a finding, but it stays correct only while the base class has no
implementation.

Two apps that override the same DocType is a separate finding: the last installed app wins and
the other override never loads. `install_app` prints a warning at install time only
(`frappe/installer.py`).
