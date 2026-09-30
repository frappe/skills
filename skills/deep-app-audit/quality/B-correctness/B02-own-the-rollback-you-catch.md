---
id: B02
area: correctness
---
# B02 — Own the rollback when you catch an exception

**Why:** The framework rolls back only when an exception reaches it. Code that catches an
exception hides the failure. The partial writes made before the failure stay in the
transaction and commit at the end of the request. The user sees success and the data is wrong.

## Bad

```python
def create_shipment_lines(order):
    for row in order.items:
        try:
            frappe.get_doc({"doctype": "Shipment Line", "item": row.item_code}).insert()
        except Exception:
            frappe.log_error("shipment line failed")
    # the rows that succeeded stay in the transaction
```

## Good

```python
from frappe.database.database import savepoint

def create_shipment_lines(order):
    for row in order.items:
        with savepoint(catch=frappe.DuplicateEntryError):
            frappe.get_doc({"doctype": "Shipment Line", "item": row.item_code}).insert()
```

## Find

- `rg -n 'except .*:' -A 4 --type py` in the app, then keep every block that catches around a
  write and does not roll back or re-raise.
- `rg -n 'except Exception:\s*$' -A 2 --type py` followed by `pass`, `continue` or
  `frappe.log_error`.
- `rg -n 'frappe\.log_error' --type py` inside an `except` block that wraps an insert, a save
  or a `frappe.db.sql` write.

## Confirm

A catch around a read, a network call or a formatting step writes nothing, so it is not a
finding. A catch that re-raises, or that throws a user error, is correct, because the framework
then rolls the transaction back itself.

`frappe.db.savepoint` and the `savepoint` context manager are the supported partial rollback
(`source:frappe/database/database.py:savepoint`). `savepoint` rolls back with
`save_point=`, which no surface blocks, so it works in a controller lifecycle method and in a
`doc_events` handler as well as in code that owns its transaction.

A rollback of the whole transaction is correct only where the caller owns the transaction
boundary, such as a patch, a bench command or the body of a scheduled job. Inside document
lifecycle code it is B01: in the controller's own method it discards work the caller did not
choose to discard, and in a `doc_events` handler it is a no-op, so the failure the handler
meant to undo stays in the transaction and commits.
