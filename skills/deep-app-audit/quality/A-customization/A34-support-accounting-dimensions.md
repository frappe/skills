---
id: A34
area: customization
---
# A34 — A DocType that posts GL entries carries the accounting dimensions

**Why:** Accounting dimensions are how a site slices its accounts. A voucher that does not carry
them writes GL rows with empty dimensions. Every dimension report is then wrong for that voucher
type, and no patch can recover the values.

**Applies to:** an app that ships a DocType which creates GL Entry rows.

## Bad

```python
# my_app/doctype/levy_voucher/levy_voucher.py
class LevyVoucher(AccountsController):
	def on_submit(self):
		self.make_gl_entries()

	def get_gl_entries(self):
		return [
			self.get_gl_dict({"account": self.levy_account, "debit": self.amount}),
			self.get_gl_dict({"account": self.payable_account, "credit": self.amount}),
		]
```

The DocType is in no hook, so it never gets the dimension fields.

## Good

```python
# my_app/hooks.py
accounting_dimension_doctypes = ["Levy Voucher", "Levy Voucher Detail"]
```

```python
# my_app/doctype/levy_voucher/levy_voucher.py
class LevyVoucher(AccountsController):
	def get_gl_entries(self):
		return [
			self.get_gl_dict({"account": self.levy_account, "debit": self.amount}, item=self),
			self.get_gl_dict({"account": self.payable_account, "credit": self.amount}, item=self),
		]
```

## Find

- `rg -n 'make_gl_entries|get_gl_dict' --type py` in the app.
- `rg -n 'accounting_dimension_doctypes' hooks.py`.
- A DocType in the first list and not in the second is the finding.

## Confirm

`get_checks_for_applicable_accounts` and the dimension setup read
`frappe.get_hooks("accounting_dimension_doctypes")`
(`erpnext/accounts/doctype/accounting_dimension/accounting_dimension.py`). Registering the
DocType is what adds the dimension fields to it when a site creates a dimension.

Both the parent and the child DocType that carries the account belong in the list. ERPNext lists
both forms for its own vouchers.

Passing `item=` to `get_gl_dict` is what copies the dimension values into the GL row. Registering
the DocType without passing the item leaves the fields on the form and empty in the ledger.

An app that only reads GL entries is not a finding.
