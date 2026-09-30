---
id: B33
area: correctness
mechanism: M11
semgrep: {rules: [frappe-after-save-controller-hook], coverage: partial}
---
# B33 — Use a lifecycle method name the framework calls

**Why:** The framework calls a fixed set of method names. A method with a name that is close
but not exact never runs. Nothing warns, because a controller may define any method it likes.
The customization looks installed and does nothing. The same holds for a misspelled key in
`doc_events`.

## Bad

```python
class PurchaseRequest(Document):
    def after_save(self):          # not a lifecycle method
        notify_buyer(self)

# hooks.py
doc_events = {"Purchase Request": {"on_submitted": "my_app.buying.notify"}}  # not an event
```

## Good

```python
class PurchaseRequest(Document):
    def on_update(self):
        notify_buyer(self)

# hooks.py
doc_events = {"Purchase Request": {"on_submit": "my_app.buying.notify"}}
```

## Find

- `rg -n 'def after_save|def before_delete|def on_saved|def after_submit|def before_load' --type py`
  in the app.
- `rg -n 'doc_events' -A 40 hooks.py`, then check every event key against the names in
  `source:frappe/model/document.py:Document.save` and `Document._submit`.
- `rg -n 'def _\w+' --type py` on a controller. `run_method` refuses a name that starts with an
  underscore (`source:frappe/model/document.py:Document.run_method`).
- `rg -n 'allow_on_submit' --type json` in the app, then check the controller for
  `on_update_after_submit`. A field editable after submit with no handler runs no validation.

## Confirm

The names the framework calls are `before_validate`, `validate`, `before_save`, `before_submit`,
`before_cancel`, `before_update_after_submit`, `on_update`, `on_submit`, `on_cancel`,
`on_update_after_submit`, `on_change`, `before_insert`, `after_insert`, `on_trash`,
`after_delete`, `before_rename`, `after_rename`, `autoname`, `before_naming`, `onload`,
`before_print`, `before_discard` and `on_discard`. A helper method with any other name is
correct as long as a lifecycle method calls it. The finding is a method that nothing calls.
Searching the app for the method name is the fastest way to prove it.
