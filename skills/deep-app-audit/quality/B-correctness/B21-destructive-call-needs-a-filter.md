---
id: B21
area: correctness
---
# B21 — A destructive database call must carry a filter that cannot be empty

**Why:** `frappe.db.delete` with no filter deletes every row of the table. A filter built from
a variable that turns out empty produces the same statement. The call runs inside the request
transaction, so nothing warns and the loss is only visible after the commit. The same holds for
a `set_value` whose filter dict is empty: it updates every row.

## Bad

```python
@frappe.whitelist()
def clear_stale_logs(reference_name=None):
    frappe.db.delete("My Sync Log", {"reference_name": reference_name})
```

## Good

```python
@frappe.whitelist()
def clear_stale_logs(reference_name: str):
    if not reference_name:
        frappe.throw(_("Reference Name is required"))
    frappe.db.delete("My Sync Log", {"reference_name": reference_name})
```

## Find

- `rg -n 'frappe\.db\.delete\(' --type py`. Keep every call whose second argument is a variable
  or is missing.
- `rg -n 'frappe\.db\.set_value\(' --type py` where the name argument is a dict built at run
  time.
- `rg -n 'delete from |truncate ' -i --type py` in raw SQL with a `where` clause built from a
  variable.
- `rg -n 'frappe\.delete_doc\(' --type py` in a loop over a query result with no filter.

## Confirm

A deliberate full-table clear, such as a log rotation on a doctype the app owns, is correct.
The finding is a filter that a caller can make empty. `frappe.db.delete` builds its statement
through `frappe.qb.get_query`, and an empty `filters` value produces no `where` clause
(`source:frappe/database/database.py:Database.delete`). `frappe.db.truncate` always clears the
whole table and is DDL, so it also commits; see B03. A guard on the caller is not enough when
the function is also reachable from a Server Script or a REST call.
