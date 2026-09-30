---
id: B01
area: correctness
mechanism: M11
semgrep: {rules: [frappe-manual-commit], coverage: partial}
---
# B01 — Do not commit or roll back inside document lifecycle code

**Why:** The caller owns the transaction, and one document save is one unit of work inside it.
A commit or a rollback that does not fit the lifecycle of the document is a defect: a commit
ends the unit early, so a later failure cannot undo what is already written, and a rollback
discards work the caller did not choose to discard. The user then sees a document that is
submitted with no ledger rows, no stock movement, or half of its child records.

**Applies to:** code that runs inside a document save: a controller lifecycle method, an
override class method, a `doc_events` handler, a workflow task, and a DocType Event Server
Script.

## Bad

```python
# my_app/overrides/delivery_note.py
class CustomDeliveryNote(DeliveryNote):
    def on_submit(self):
        super().on_submit()
        for row in self.items:
            push_row_to_wms(row)
            frappe.db.commit()  # ends the transaction before stock validation runs
```

## Good

```python
# my_app/overrides/delivery_note.py
class CustomDeliveryNote(DeliveryNote):
    def on_submit(self):
        super().on_submit()
        frappe.enqueue(
            "my_app.wms.push_delivery_note",
            name=self.name,
            enqueue_after_commit=True,
        )
```

## Find

- `rg -n 'frappe\.db\.(commit|rollback)\(' --type py` in the app. Keep every hit inside a
  controller method, a hooked handler, a mapper, or an override class.
- `rg -n 'db_set\([^)]*commit\s*=\s*True' --type py`. `Document.db_set` commits when
  `commit=True`.
- `rg -n '_disable_transaction_control|auto_commit_on_many_writes|autocommit' --type py`.
  Setting `frappe.db.auto_commit_on_many_writes` turns one transaction into many. It is the
  common wrong answer to `TooManyWritesError`, which the framework raises above 200,000 writes
  in one action (`source:frappe/database/database.py:Database.check_transaction_status`).
- Server Script records: `script LIKE '%commit%'` on `script_type = "DocType Event"`.

## Confirm

Judge the call against the lifecycle of the document, not against the surface it sits on. A
commit or a rollback that ends the save of the document early, or that discards a part of it,
is a finding. A commit in code that owns its own transaction boundary is correct: a patch, a
bench command, the body of a scheduled job, and a data import each own the boundary, so a
commit there is not this rule. A rollback inside a `try` block that catches an exception is
B02, not this rule.

The surface then tells the reader what a hit does, and both outcomes are findings.

A call in the controller's own lifecycle method, including an `override_doctype_class` method,
really commits or really rolls back. The transaction guard wraps the hooked handlers only, not
the method the controller defines (`source:frappe/model/document.py:compose`). The result is a
partial write that no later failure can undo.

A call in a `doc_events` handler is a no-op. The framework raises
`frappe.db._disable_transaction_control` around the handler, so `commit()` and `rollback()`
warn and return (`source:frappe/database/database.py:Database.commit`). Nothing is written
early, and the commit the author wanted never happens. The handler is written for an effect it
does not get, so the code that follows it is built on a wrong assumption. In a DocType Event
Server Script the names are not there at all: `safe_exec` removes `commit`, `rollback` and
`add_index` from the script namespace, so the script raises
(`source:frappe/utils/safe_exec.py:safe_exec`).

`rollback(save_point=...)` is not blocked on any of these surfaces, and it rolls back to the
savepoint only. It is the supported partial rollback and is not a finding here. See B02.

On version 15 and earlier there is no guard, so every call on every one of these surfaces
really commits or really rolls back.
