---
id: B27
area: correctness
---
# B27 — Change a child row through its parent

**Why:** A child row has no life of its own. The parent's `validate` recomputes the fields the
child derives, and the parent's save writes the whole table. A direct write to a child row is
overwritten by the next parent save, and it never triggers the parent's recalculation of the
totals that depend on it.

## Bad

```python
def apply_row_discount(invoice, item_row, rate):
    frappe.db.set_value("Sales Invoice Item", item_row, "rate", rate)
    # the parent's grand_total still holds the old rate
```

## Good

```python
def apply_row_discount(invoice, item_row, rate):
    doc = frappe.get_doc("Sales Invoice", invoice)
    for row in doc.items:
        if row.name == item_row:
            row.rate = rate
    doc.save()
```

## Find

- `rg -n 'frappe\.db\.set_value\(\s*"[^"]+ (Item|Detail|Row)"' --type py`.
- `rg -n 'set_value\(' --type py` where the first argument is a doctype whose JSON has
  `"istable": 1`.
- `rg -n 'frappe\.get_doc\("[^"]+ Item"' --type py` followed by `save()`. Saving a child
  document on its own does not run the parent's validation.
- JavaScript: `rg -n 'frm\.doc\.\w+\.push\(' --type js` with no `frm.refresh_field`. See B45.

## Confirm

A hidden bookkeeping field on a child row, which no parent computation reads, can be written
directly, and `db_set` on the parent for the same purpose is the clearer form. The finding is a
field that the parent recomputes. `frappe.db.set_value` on a child row runs no validation and
no event; see B28. A child row is also lost when the client sends a table that does not include
it: the save replaces the whole table with what it received.
