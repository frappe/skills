---
id: B16
area: correctness
---
# B16 — Treat every database read as possibly empty

**Why:** This is the largest failure group in both the public tracker and the support corpus.
`frappe.db.get_value` returns `None` when no row matches. `frappe.db.exists` returns the name
or `None`. A link field holds an empty string. A child table can be empty. Code that indexes,
unpacks or calls a method on such a value raises `AttributeError` or `TypeError` on submit, and
the user cannot act on the message.

## Bad

```python
def get_default_warehouse(company):
    return frappe.db.get_value("Company", company, "default_warehouse").strip()

def get_first_item_rate(doc):
    return doc.items[0].rate
```

## Good

```python
def get_default_warehouse(company):
    warehouse = frappe.db.get_value("Company", company, "default_warehouse")
    return (warehouse or "").strip()

def get_first_item_rate(doc):
    if not doc.items:
        return 0.0
    return flt(doc.items[0].rate)
```

## Find

- `rg -n 'get_value\([^)]*\)\.' --type py` and `rg -n 'get_value\([^)]*\)\[' --type py`.
- `rg -n 'get_cached_value\(' --type py`. It returns `None` instead of raising from version 14.
- `rg -n '\.items\[0\]|\[0\]\.' --type py` on a child table or a query result.
- `rg -n 'frappe\.db\.get_value\([^)]*\[' --type py` where the call asks for several fields.
  The result is a list, and it is `None` when no row matches, so the unpack fails.
- JavaScript: `rg -n 'frm\.doc\.__onload\.' --type js` without `?.`.

## Confirm

A read of a mandatory field on a document that was just loaded cannot be empty, unless the
field became mandatory after the row was written; B13 covers that case. A read whose result
feeds a truth test needs no guard. The precise question is whether the value can be empty on
any site, not on the site the author tested. A link field to a disabled or deleted master is
the common source. `frappe.db.get_value(dt, None, field)` on a doctype that is not Single
returns the first row of the table, not `None`
(`source:frappe/database/database.py:Database.get_value`), which hides the bug.
