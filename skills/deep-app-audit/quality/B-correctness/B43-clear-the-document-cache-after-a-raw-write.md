---
id: B43
area: correctness
---
# B43 — Clear the document cache after a write that bypasses the ORM

**Why:** `frappe.get_cached_doc` and `frappe.get_cached_value` read from Redis. `doc.save` and
`frappe.db.set_value` clear that entry. Raw SQL does not. Every later reader in every worker
then gets the old document, until the key expires or the site is restarted. The symptom is a
setting that does not take effect and a value that is right in the list view and wrong in the
form.

## Bad

```python
def deactivate_routes(region):
    frappe.db.sql(
        "update `tabRoute` set is_active = 0 where region = %s", region
    )
```

## Good

```python
def deactivate_routes(region):
    names = frappe.get_all("Route", filters={"region": region}, pluck="name")
    frappe.db.sql(
        "update `tabRoute` set is_active = 0 where region = %s", region
    )
    for name in names:
        frappe.clear_document_cache("Route", name)
```

## Find

- `rg -n 'frappe\.db\.sql\(' --type py` with `update`, `insert` or `delete`, then look for a
  matching `frappe.clear_document_cache` or `frappe.clear_cache`.
- `rg -n 'get_cached_doc\(|get_cached_value\(' --type py` on a doctype that the app also writes
  with raw SQL.
- `rg -n 'frappe\.db\.bulk_update\(' --type py`. It writes many rows in one statement and runs
  no document event.
- `rg -n 'Property Setter|Custom Field' --type py` written by app code with no
  `frappe.clear_cache(doctype=...)` after it. Meta is cached too.

## Confirm

`frappe.db.set_value` and `doc.save` clear the entry themselves, so they are not findings.
`frappe.clear_document_cache` removes the Redis key at once and again after commit and after
rollback, so it is safe to call before the write as well
(`source:frappe/model/document.py:clear_document_cache`). A doctype that no code reads through
`get_cached_doc` has no stale reader, so the finding drops. Meta changes need
`frappe.clear_cache(doctype=...)`, which is a different key set. Cache scope and cache cost
belong to the performance rules; this rule is only about a reader that gets the wrong value.
