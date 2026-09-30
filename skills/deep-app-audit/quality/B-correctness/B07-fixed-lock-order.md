---
id: B07
area: correctness
---
# B07 — Take locks in the same order in every transaction

**Why:** A deadlock is two transactions that take the same locks in a different order. The
database kills one of them. Faster code makes the window smaller but never removes the
deadlock. Only a fixed lock order removes it. Every write locks the rows it touches and the
gaps around them, so a loop over an unsorted list takes locks in the order the list happens to
have.

## Bad

```python
def transfer(from_bin, to_bin, qty):
    frappe.db.get_value("Bin", from_bin, "actual_qty", for_update=True)
    frappe.db.get_value("Bin", to_bin, "actual_qty", for_update=True)
    ...
```

## Good

```python
def transfer(from_bin, to_bin, qty):
    for bin_name in sorted([from_bin, to_bin]):
        frappe.db.get_value("Bin", bin_name, "actual_qty", for_update=True)
    ...
```

## Find

- `rg -n 'for_update\s*=\s*True' --type py`, then check whether two locks in one function can
  be taken in either order.
- `rg -n 'for .* in ' -A 6 --type py` where the loop body writes rows and the list comes from a
  set, a dict, or an unordered query.
- `rg -n 'order_by' --type py` missing on a `get_all` whose result feeds a write loop.
- Error Log entries with `Query deadlocked`. The framework logs these on MariaDB
  (`source:frappe/database/database.py:Database.sql`).

## Confirm

A single lock per transaction cannot deadlock. Two transactions that touch different rows
cannot deadlock. A lock wait timeout is a different problem: it means one transaction holds a
lock too long, and the fix is a shorter transaction, not a lock order. Sort by the primary key,
because that is the order the database itself uses.
