---
id: A41
area: customization
---
# A41 — Never write a ledger row directly. Write the transaction that owns it

**Why:** A ledger row is a derived record. Its value is a function of the transaction that
created it, and only the transaction controller may write it. An app that inserts, updates or
deletes a GL Entry, a Stock Ledger Entry, a Payment Ledger Entry or a Bin row breaks that
function. The document and its ledger then disagree, no report can be trusted, and cancelling
the transaction does not remove a row the transaction did not create.

**Applies to:** an app that customizes ERPNext accounting or stock.

## Bad

```python
def fix_missing_gl(doc, method=None):
    frappe.get_doc({
        "doctype": "GL Entry",
        "account": doc.rounding_account,
        "debit": doc.rounding_adjustment,
        "voucher_no": doc.name,
    }).insert(ignore_permissions=True)
```

## Good

```python
# my_app/overrides/sales_invoice.py
class CustomSalesInvoice(SalesInvoice):
    def get_gl_entries(self, warehouse_account=None):
        entries = super().get_gl_entries(warehouse_account)
        entries.append(
            self.get_gl_dict({
                "account": self.rounding_account,
                "debit": self.rounding_adjustment,
            })
        )
        return entries
```

## Find

- `rg -n '"(GL Entry|Stock Ledger Entry|Payment Ledger Entry|Bin|Serial and Batch Bundle)"' --type py`
  in the app.
- `rg -n 'tabGL Entry|tabStock Ledger Entry|tabBin' --type py` in raw SQL with `insert`,
  `update` or `delete`.
- `rg -n 'frappe\.db\.set_value\(\s*"(GL Entry|Stock Ledger Entry|Bin)"' --type py`.
- Server Script records whose `reference_doctype` is a ledger doctype.
- A patch or a bench command that repairs a ledger row in place.

## Confirm

The rule is about which doctypes the app writes, so read the doctype name, not the mechanism.
An insert, an update or a delete of a ledger doctype is a finding wherever it is written: an
override class, a hooked handler, a whitelisted method, a Server Script, a patch, or raw SQL.

Reading a ledger row is correct. Extending `get_gl_entries` or `get_sl_entries` on the
transaction controller is the supported way to add a row, because cancel then removes it too. A
row written through the controller carries the voucher reference that the cancel path reads; a
row written directly does not, which is how a reader tells the two apart.

A Bin row is the same failure with a different table. The quantity it holds is a sum of the
stock ledger, so a direct write makes it disagree with the rows it summarises.

A handler that only edits a field on a ledger row the framework created is the weaker,
mechanism-level form of this failure. That is A06.
