---
id: B29
area: correctness
semgrep: {rules: [frappe-modifying-but-not-comitting, frappe-modifying-but-not-comitting-other-method], coverage: partial}
---
# B29 — A change made after the write step needs `db_set`

**Why:** The framework writes the row before it calls `on_update`, `on_submit`, `on_cancel`,
`after_insert` and `on_update_after_submit`. An attribute set in one of those methods changes
the in-memory document only. It is lost as soon as the request ends. The value appears correct
to the code that runs next in the same request, which is why the bug survives testing.

## Bad

```python
class ShipmentRequest(Document):
    def on_submit(self):
        self.tracking_number = book_with_carrier(self)  # never reaches the database
```

## Good

```python
class ShipmentRequest(Document):
    def on_submit(self):
        self.db_set("tracking_number", book_with_carrier(self))
```

## Find

- `rg -n 'def (on_update|on_submit|on_cancel|after_insert|on_update_after_submit)' -A 25 --type py`
  in the app, then keep every `self.<field> = ` with no matching `db_set` or `save`.
- The same shape through a helper: a method called from one of those hooks that assigns to
  `self`.
- `doc_events` handlers on the same events that assign to `doc.<field>`.
- `rg -n 'self\.set\("' --type py` inside a post-write hook.

## Confirm

An assignment to a non-persisted attribute, such as `self.flags.something` or a name that is
not a field on the DocType, is correct and is a common false positive of the semgrep rule. An
assignment followed by `self.save()` in the same hook is a different bug: it re-enters the save
cycle and can loop. `db_set` is the supported form. In `validate`, `before_save`,
`before_submit` and `before_insert` a plain assignment is correct, because the write has not
happened yet.
