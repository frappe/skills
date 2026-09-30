---
id: B08
area: correctness
---
# B08 — Give a repeatable endpoint or job a deduplication key

**Why:** A caller retries after a timeout. A user clicks twice. A queue redelivers a job. Work
that has no key runs a second time and creates a second document. The second run is invisible
until someone reads the ledger, because both documents are valid on their own.

## Bad

```python
@frappe.whitelist()
def create_delivery(sales_order):
    doc = frappe.get_doc({"doctype": "Delivery Note", "sales_order": sales_order})
    doc.insert()
    frappe.enqueue("my_app.tasks.notify_carrier", name=doc.name)
    return doc.name
```

## Good

```python
@frappe.whitelist()
def create_delivery(sales_order, request_id):
    if name := frappe.db.get_value("Delivery Note", {"external_request_id": request_id}):
        return name
    doc = frappe.get_doc({
        "doctype": "Delivery Note",
        "sales_order": sales_order,
        "external_request_id": request_id,  # a unique field on the DocType
    })
    doc.insert()
    frappe.enqueue(
        "my_app.tasks.notify_carrier",
        name=doc.name,
        job_id=f"notify_carrier::{doc.name}",
        deduplicate=True,
        enqueue_after_commit=True,
    )
    return doc.name
```

## Find

- `rg -n '@frappe\.whitelist' -A 20 --type py` in the app. Keep every endpoint that inserts a
  document and takes no caller-supplied key.
- `rg -n 'frappe\.enqueue\(' --type py` with no `job_id`. `deduplicate=True` needs `job_id`
  (`source:frappe/utils/background_jobs.py:enqueue`).
- `rg -n 'scheduler_events' hooks.py`, then check each handler for a marker that says the work
  is done, such as a status field or a log row.
- `rg -n 'requests\.(get|post)\(' -A 10 --type py` for an outbound call retried without a key.

## Confirm

A read-only endpoint needs no key. An endpoint that writes a value derived only from its input,
on a row named by that input, is already idempotent. A unique index on the key field is the
only form that holds under concurrency: a plain existence check before the insert is B05.
`job_id` deduplicates only while the job is queued or started
(`source:frappe/utils/background_jobs.py:is_job_enqueued`), so it does not stop a repeat after
the first job finished. For that case the key must live in the database.
