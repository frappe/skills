---
id: B04
area: correctness
mechanism: M11
semgrep: {rules: [frappe-enqueue-without-after-commit], coverage: partial}
---
# B04 — Enqueue a job after commit when it reads what the request wrote

**Why:** A worker picks a job up in milliseconds. The request that enqueued it may not have
committed yet. The worker runs in its own transaction and reads the snapshot from before the
write. The job then works on the old value, or fails because the document does not exist.

## Bad

```python
class SalesOrder(Document):
    def on_submit(self):
        frappe.enqueue("my_app.tasks.build_pick_list", name=self.name)
```

## Good

```python
class SalesOrder(Document):
    def on_submit(self):
        frappe.enqueue(
            "my_app.tasks.build_pick_list",
            name=self.name,
            enqueue_after_commit=True,
        )
```

## Find

- `rg -n 'frappe\.enqueue(_doc)?\(' -A 6 --type py` in the app, then keep every call in a
  lifecycle method or a whitelisted method that has no `enqueue_after_commit=True`.
- `rg -n 'frappe\.enqueue\(' -A 6 --type py` with `now=True` or `is_async=False` in a request
  path. Those run inline and hold the web worker.
- `rg -n 'publish_realtime' --type py` in a lifecycle method. The client reloads the document
  and reads the old row for the same reason.

## Confirm

A job that takes every value it needs as an argument, and reads nothing from the database,
is safe without the flag. A job enqueued from a scheduled job or from a bench command runs
after that caller commits, so the flag changes nothing there. `doc.queue_action` already
enqueues after commit and takes a document lock
(`source:frappe/model/document.py:Document.queue_action`). MariaDB runs at repeatable read, so
the worker's snapshot is fixed when its first statement runs, not when it reads the row.
