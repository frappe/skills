---
id: M11
---
# M11 — Lifecycle methods on `Document`

**What:** The framework calls a fixed set of method names on a controller as a document moves
through save, submit, cancel, rename, and delete. `run_before_save_methods` runs
`before_validate`, then `validate` and `before_save` for a save, `validate` and `before_submit`
for a submit, `before_cancel` for a cancel, and `before_update_after_submit` for an update after
submit. `run_post_save_methods` runs `on_update` for a save, `on_update` and `on_submit` for a
submit, `on_cancel` for a cancel, `on_update_after_submit` for an update after submit, and then
`on_change` for every one of them. Insert adds `before_insert` and `after_insert`. Other names
the framework calls are `autoname`, `before_naming`, `onload`, `before_print`, `before_rename`,
`after_rename`, `on_trash`, `after_delete`, `before_discard`, and `on_discard`.

**Guards:** `run_method` refuses a name that starts with `_`. `Document.hook` collates the
return values: a dict is merged into the collected dict, and any other value replaces whatever
was collected, so a lifecycle method that returns a value produces a result nobody reads and
which another app can overwrite. The row is written before `on_update`, `on_submit`,
`on_cancel`, and `on_update_after_submit` run, so a change made to `self` in those methods is
not persisted by the save that called them. `check_no_back_links_exist` runs after `on_cancel`.

`_disable_transaction_control` is raised around the `doc_events` handlers only. A `commit` or a
`rollback` inside the controller's own `validate` or `on_submit` is not blocked by the
framework, and it does end the request's transaction.

## Good use

Choose the method by what the code needs to see and what it is allowed to change.

- `before_validate`: normalize input the user typed, before any rule reads it.
- `validate`: compute derived fields and raise on anything the document must not be. It runs on
  every save, so it must give the same result every time it runs on the same input.
- `before_save`: last chance to change the document. Use it for values that depend on the final
  validated state.
- `on_update`, `on_submit`, `on_cancel`: side effects on other documents. The row is already
  written.
- `on_change`: runs after a save and also after `db_set`, so keep it cheap and free of writes to
  the same document.

```python
class HaulageNote(Document):
    def validate(self):
        self.total_weight = sum(flt(row.weight) for row in self.items)

    def on_submit(self):
        self.create_trip_log()

    def on_cancel(self):
        self.cancel_trip_log()
```

Rebuild a generated child table instead of appending to it. `validate` runs on every save, so an
append adds one more row each time the user presses save.

Compute a field from stored input only. A field that reads its own previous value drifts on the
second save.

Persist a change made after the write step with `db_set`. Assigning to `self` in `on_update` has
no effect on the row.

Write lifecycle code that does not know how it was called. The same `validate` runs from the
desk, from the REST API, from a background job, from a patch, and from a data import, so it must
not read `frappe.form_dict`, `frappe.request`, or `frappe.session` for a decision.

Keep the transaction whole. Let an exception reach the framework and let the framework roll back
and commit. Do not call `frappe.db.commit()` to "save progress".

Keep the cost small. Every query added to `validate` or `onload` is paid on every save and every
form load of that DocType. Never call an external service from a lifecycle method: it puts a
third party in the path of every save.

Validate an update after submit. A field marked "Allow on Submit" can be changed on a submitted
document, and only `before_update_after_submit` and `on_update_after_submit` see that change.

## Rules

- B01 — Do not commit or roll back inside document lifecycle code
- B02 — Own the rollback when you catch an exception
- B04 — Enqueue a job after commit when it reads what the request wrote
- B09 — A computed field must be a function of stored input, not of itself
- B10 — Rebuild a generated child table instead of appending to it
- B25 — One owner writes a status field
- B29 — A change made after the write step needs `db_set`
- B31 — Lifecycle code must not read request state
- B33 — Use a lifecycle method name the framework calls
- B34 — Validate an update after submit, and do not allow one on a field with ledger meaning
- B35 — A validation must run in every path that can change the data it protects
