---
id: M12
---
# M12 — `doc_events`

**What:** `doc_events` in `hooks.py` maps a DocType and a method name to one or more dotted
paths. The framework calls those handlers after the controller's own method for that event. The
DocType key may be a tuple, which `get_doc_hooks` expands into one entry per DocType, and it may
be `*`, which matches every DocType. This is how an app adds behaviour to a DocType another app
owns.

**Guards:** Handlers for the DocType run first, then handlers registered under `*`. Within one
key, handlers run in the order the merged hook list gives them, which is app order. Every
handler runs with `_disable_transaction_control` raised, so `frappe.db.commit()` and
`frappe.db.rollback()` warn and do nothing. A handler is called as `handler(doc, method)`, and
also as `handler(doc)` when the handler declares no second parameter and the event passes no
positional argument. Return values go through the same collation as a lifecycle method: a dict
merges, anything else replaces.

## Good use

Register the handler on the document that owns the decision, and keep the handler in a module
named for what it does.

```python
# my_app/hooks.py
doc_events = {
    "Sales Invoice": {
        "on_submit": "my_app.permits.stamp_permit_number",
    },
    ("Sales Invoice", "Delivery Note"): {
        "on_cancel": "my_app.permits.release_permit_number",
    },
}
```

```python
# my_app/permits.py
def stamp_permit_number(doc, method=None):
    ...
```

Hook the transaction, not the record the transaction derives. A handler on GL Entry or Stock
Ledger Entry edits a projection that core recomputes, and it runs once per row. The same rule on
the Sales Invoice runs once and survives a core change to how the rows are built.

Accept the arguments the call site passes. Give the handler a `method` parameter with a default,
so it works for every event.

Return early. A handler on a high-volume DocType is on the write path of every save of that
DocType across every app on the site. Read the cheap condition first, and make no query when the
handler has nothing to do.

Do not depend on another handler having run. App order decides the order, and the site owner
decides app order. Two handlers that must run in sequence belong in one handler.

Do not commit and do not roll back. The framework blocks both here, and code that tries is
relying on an effect that does not happen.

Do not change another app's document in a way its own `validate` did not check. Set a field
through the owning document's API, or raise, but do not write a value the owner would have
rejected.

Use `*` sparingly. A handler under `*` runs for every save of every DocType on the site,
including Version, Error Log, and every log row.

## Rules

- A06 — Attach business logic to the transaction, not to the ledger entry it creates
- A25 — A hook handler accepts every argument the call site passes
- B32 — A handler must not depend on the run order of another handler
- B01 — Do not commit or roll back inside document lifecycle code
