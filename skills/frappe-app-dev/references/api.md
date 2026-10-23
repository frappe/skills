# Whitelisted APIs

## Preferred: Methods in DocType controllers

Place whitelisted methods in the controller file — either as Document class methods (doc-level) or as module-level functions (doctype-level). This avoids needing full dotted paths to call them.

### Doc-level methods (on a specific document)

```python
# apps/<app>/<app>/<module>/doctype/expense/expense.py

import frappe
from frappe.model.document import Document

class Expense(Document):
    @frappe.whitelist()
    def approve(self):
        self.status = "Approved"
        self.save()
        return self.status
```

Call from client JS:
```javascript
frappe.call({
    method: "approve",       // just the method name
    doc: frm.doc,
    callback(r) { console.log(r.message); }
});
// or
frm.call("approve");
```

Call from HTTP (v2 API):
```
POST /api/v2/document/Expense/EXP-0001/method/approve
```

### DocType-level functions (module root)

```python
# apps/<app>/<app>/<module>/doctype/expense/expense.py

import frappe

@frappe.whitelist()
def get_expense_summary(status=None):
    filters = {"status": status} if status else {}
    return frappe.get_list("Expense", filters=filters, fields=["name", "title", "amount"])
```

Call from client JS:
```javascript
frappe.call({
    method: "myapp.mymodule.doctype.expense.expense.get_expense_summary",
    args: { status: "Draft" },
    callback(r) { console.log(r.message); }
});
```

Call from HTTP:
```
POST /api/v2/method/Expense/get_expense_summary
```

## Standalone API files (for non-DocType logic)

Use only when logic doesn't belong to any DocType:

```python
# apps/<app>/<app>/api.py
import frappe

@frappe.whitelist()
def get_dashboard_data():
    # Counts only the Expenses the caller can read. frappe.db.count ignores permissions
    result = frappe.get_list("Expense", fields=[{"COUNT": "*", "as": "total"}])
    return {"total": result[0].total}
```

For larger apps, organize by feature:
```
apps/<app>/<app>/api/
    __init__.py
    expenses.py
    reports.py
```

## Allow guest access

```python
@frappe.whitelist(allow_guest=True)
def public_endpoint():
    return {"message": "Hello"}
```

## Argument handling

- **Always add type hints** to whitelisted method parameters. Frappe validates and casts arguments based on type hints, preventing type-confusion attacks:
```python
@frappe.whitelist()
def create_expense(title: str, amount: float, tags: list | None = None):
    # title is guaranteed to be str, amount is cast to float
    # Without type hints, all args arrive as untrusted strings
    ...
```

- Use `frappe.form_dict` for raw request data:
```python
data = frappe.form_dict
```

## Return values

- Return a dict/list → auto-serialized to JSON under `{"message": <return_value>}`
- For custom HTTP responses:
```python
frappe.response["meta"] = meta
```

## Built-in document APIs (v2)

Frappe provides CRUD APIs automatically via `/api/v2/document/` — no need to write them. Requires **Frappe v15+**.

```
GET    /api/v2/document/<DocType>                          # list (with filters, fields, order_by, limit)
POST   /api/v2/document/<DocType>                          # create
GET    /api/v2/document/<DocType>/<name>/                  # read
PUT    /api/v2/document/<DocType>/<name>/                  # update
DELETE /api/v2/document/<DocType>/<name>/                  # delete
GET    /api/v2/document/<DocType>/<name>/copy              # copy doc
POST   /api/v2/document/<DocType>/<name>/method/<method>/  # call doc method
POST   /api/v2/method/<DocType>/<method>                   # call doctype level method
GET    /api/v2/doctype/<DocType>/meta                      # get DocType meta
GET    /api/v2/doctype/<DocType>/count                     # count records
```

### List query params
`fields` (JSON list), `filters` (JSON dict/list), `order_by`, `start`, `limit` (default 20), `group_by`.

Response includes `has_next_page` boolean for pagination.

### Bulk operations
```
POST /api/v2/document/<DocType>/bulk_delete   # body: {"names": [...]}
POST /api/v2/document/<DocType>/bulk_update   # body: {"docs": [{"name": "...", ...fields}]}
```

Large bulk operations (>20 items by default) are automatically enqueued as background jobs.

Only create custom `@frappe.whitelist()` endpoints for logic that goes beyond CRUD.

## Read records with `get_list`, not `get_all`

A whitelisted method is reachable by any caller who passes its decorator, so its reads must apply the caller's permissions.

| Call | Applies permissions? |
|---|---|
| `frappe.get_list` | Yes: role permissions, user permissions, shared documents, "if owner" rules and `permission_query_conditions` |
| `frappe.get_all` | No. Returns every matching record |
| `frappe.get_list(..., ignore_permissions=True)` | No. Same as `get_all` |
| `frappe.db.get_value`, `exists`, `count`, `sql` | No |
| `frappe.qb.get_query` | No, by default (`ignore_permissions=True`) |

A `get_all` in a whitelisted method lets a caller read records they can't open through `/api/resource/<DocType>` or the list view. When the method also takes `filters` or `fields` from the request, the caller chooses which records and fields come back.

```python
# Wrong: any logged-in user gets every Expense
@frappe.whitelist(methods=["GET"])
def get_expenses(status: str):
    return frappe.get_all("Expense", filters={"status": status}, fields=["name", "amount"])

# Right: returns only the Expenses the caller can read
@frappe.whitelist(methods=["GET"])
def get_expenses(status: str):
    return frappe.get_list("Expense", filters={"status": status}, fields=["name", "amount"])
```

Use `get_all` only when the method must read beyond the caller's permissions, for example an aggregate over records the caller can't open. In that case:

- Check first that the caller may see *everything* the query returns. `frappe.has_permission("Expense")` without a document isn't enough: a user who can only read their own Expenses passes it. Gate on a role (`frappe.only_for("Expense Approver")`), or on `doc.check_permission("read")` for each document the query reads.
- Hardcode `filters` and `fields`. Never pass request values through unchecked.
- Return only the fields the caller needs.

`get_all` stays the right choice in code no request reaches directly: controller hooks, background jobs, patches and scheduled tasks.

### Child tables

Child tables (`istable: 1`) have no permissions of their own. They take them from the parent. So `frappe.get_list("Expense Item")` raises `PermissionError`, because Frappe doesn't know which parent to check.

Passing `parent_doctype="Expense"` stops the error, but only checks that the caller can read *some* Expense. It still returns rows from Expenses the caller can't open. Instead:

```python
# Rows from many parents: query the parent and select child fields.
# Permissions on Expense decide which rows come back
frappe.get_list("Expense", fields=["name", "items.description", "items.amount"])

# Rows from one parent: check that parent, then read its rows
expense = frappe.get_doc("Expense", name)
expense.check_permission("read")
return expense.items
```

## Specify HTTP methods

Always declare allowed HTTP methods explicitly. Frappe auto-commits only for POST/PUT — GET requests do not commit.

```python
@frappe.whitelist(methods=["GET"])
def get_dashboard_data(): ...

@frappe.whitelist(methods=["POST"])
def submit_entry(name: str): ...

@frappe.whitelist(methods=["GET", "POST"])
def get_or_create_token(): ...
```

## Anti-patterns

- **Don't wrap doc methods in standalone APIs.** If the controller has `@frappe.whitelist()` on a method, clients call it directly via `frm.call("approve")` or `POST /api/v2/document/Expense/EXP-001/method/approve`. Don't create a separate `api.py` function that just fetches the doc and calls the same method.
- **Don't put doc-scoped logic in standalone APIs.** If the function fetches one doc, validates the caller, and acts on that doc — it belongs as a doc-level `@frappe.whitelist()` method, not in `api/`. Reserve standalone APIs for cross-document operations, aggregations, or endpoints with no document context.
- **Don't use `get_all` to answer a request.** Use `frappe.get_list` so the caller only sees records they can read. See [Read records with `get_list`](#read-records-with-get_list-not-get_all).
- **Don't leak sensitive fields in guest APIs.** With `allow_guest=True`, only return fields guests need. Never expose `user` (email), internal IDs, or permission-sensitive data.
