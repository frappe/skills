---
id: A07
area: customization
---
# A07 — Reuse the DocType the stack already models

**Why:** A parallel master or a parallel transaction carries none of the core logic that the
standard one carries. Submit works and cancel does not, because the copied posting code has no
reversal. Every later core fix misses the copy.

## Bad

```python
# my_app/doctype/branch_transfer_note/branch_transfer_note.py
from erpnext.stock.stock_ledger import make_sl_entries


class BranchTransferNote(Document):
	def on_submit(self):
		entries = []
		for row in self.items:
			entries.append(
				{
					"item_code": row.item_code,
					"warehouse": row.target_warehouse,
					"actual_qty": row.qty,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
				}
			)
		make_sl_entries(entries)
```

## Good

```python
# my_app/branch_transfer.py
import frappe


def make_branch_transfer(source_warehouse, target_warehouse, items):
	"""Create a Material Transfer Stock Entry with the app's own Stock Entry Type."""
	entry = frappe.new_doc("Stock Entry")
	entry.stock_entry_type = "Branch Transfer"
	entry.purpose = "Material Transfer"
	for item in items:
		entry.append(
			"items",
			{
				"item_code": item.item_code,
				"qty": item.qty,
				"s_warehouse": source_warehouse,
				"t_warehouse": target_warehouse,
			},
		)
	entry.insert()
	entry.submit()
	return entry
```

## Find

- `rg -n 'make_sl_entries|make_gl_entries|get_gl_dict|StockController|AccountsController' --type py`
  in an app that is not ERPNext.
- An app DocType with a `company` field, an `is_submittable` flag, and an `items` child table
  that has no link to a standard transaction.
- An app DocType named like a standard master: `Customer Master`, `Item List`, `Employee Record`,
  `Contact Detail`.

## Confirm

Subclassing `AccountsController` or `StockController` from an app DocType is not a finding on
its own. The core class carries the posting and the reversal together. A finding needs the app
to build the ledger payload itself.

For a parallel master, check whether the standard DocType can carry the extra data as Custom
Fields. When it can, the app duplicates a master. When the new concept is genuinely different,
even with overlapping fields, a new DocType is correct.

An app that models a country-specific document with no standard counterpart is not a finding.
