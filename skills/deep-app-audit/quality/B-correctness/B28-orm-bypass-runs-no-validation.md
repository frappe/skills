---
id: B28
area: correctness
---
# B28 — A write that bypasses the ORM runs no validation and no event

**Why:** `frappe.db.set_value`, `doc.db_set`, `frappe.db.bulk_update`, `doc.db_update` and raw
SQL write the column and nothing else. No `validate`, no `on_update`, no notification, no
webhook, no version row, and no linked-document update. Code that uses one of them because it
is faster silently drops every rule that depends on the change.

## Bad

```python
def close_expired_tasks():
    frappe.db.sql("update `tabTask` set status = 'Cancelled' where exp_end_date < %s", nowdate())
    # no version history, no notification, no parent project update, no cache clear
```

## Good

```python
def close_expired_tasks():
    names = frappe.get_all(
        "Task",
        filters={"exp_end_date": ("<", nowdate()), "status": ("!=", "Cancelled")},
        pluck="name",
    )
    for name in names:
        doc = frappe.get_doc("Task", name)
        doc.status = "Cancelled"
        doc.save()
```

## Find

- `rg -n 'frappe\.db\.(set_value|sql|bulk_update)\(' --type py` in the app, then ask what the
  controller does on that field.
- `rg -n 'db_set\(' --type py` on a field that another doctype fetches or that a status
  computation reads.
- `rg -n 'db_insert\(|db_update\(' --type py`. Both are for Virtual DocTypes only.
- `rg -n 'update `tab' -i --type py` in raw SQL.

## Confirm

A bypass is the right tool for a hidden field, a counter, a log timestamp, or a bulk correction
in a patch where the events must not fire. It is the wrong tool whenever a rule depends on the
value. `doc.db_set` does run `before_change` and `on_change`
(`source:frappe/model/document.py:Document.db_set`), so a handler on `on_change` still fires;
`frappe.db.set_value` fires nothing. Raw SQL also leaves the document cache stale; see B43.
The `modified` timestamp is another consequence: raw SQL leaves it unchanged, so every
downstream sync that pages on `modified` misses the row.
