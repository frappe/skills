---
id: B06
area: correctness
---
# B06 — Lock the rows you are about to change, and lock the children with the parent

**Why:** Under repeatable read every plain read in a transaction sees the snapshot from the
start of that transaction. Only a `FOR UPDATE` read sees the committed present and blocks
other writers. Code that reads a balance, computes a new one, and writes it back loses the
update made by a parallel worker. A lock on the parent alone gives a document that mixes a new
parent with old child rows.

## Bad

```python
def consume_credit(customer, amount):
    balance = frappe.db.get_value("Credit Account", customer, "balance")
    frappe.db.set_value("Credit Account", customer, "balance", balance - amount)
```

## Good

```python
def consume_credit(customer, amount):
    balance = frappe.db.get_value(
        "Credit Account", customer, "balance", for_update=True
    )
    if balance < amount:
        frappe.throw(_("Credit limit reached for {0}").format(customer))
    frappe.db.set_value("Credit Account", customer, "balance", balance - amount)
```

## Find

- `rg -n 'get_value\(|get_all\(|get_doc\(' -A 6 --type py` where the value read is written back
  in the same function, without `for_update=True`.
- `rg -n 'for_update\s*=\s*True' --type py`, then read the filter. A filter on a field with no
  index locks every row the scan reads.
- `rg -n 'for_update' --type py` on a parent doctype with no matching lock on its child table.
- `rg -n 'isolation level' -i --type py`. Lowering the isolation level is not an answer.

## Confirm

A read that only reports a value needs no lock. A write that does not depend on the value it
overwrites needs no lock. A row that only one worker can ever touch, such as a row keyed on the
current job id, needs no lock.

`frappe.db.get_value` accepts `for_update`, `skip_locked` and `wait`
(`source:frappe/database/database.py:Database.get_value`). `skip_locked=True` suits queue
pickup. `wait=False` fails fast instead of waiting. `frappe.qb.get_query` takes the same three
options. A file lock through `frappe.utils.synchronization.filelock` serialises work that is
not one database row, such as a token refresh.
