---
id: B25
area: correctness
---
# B25 — One owner writes a status field

**Why:** A status is derived state. The standard controller recomputes it from the document and
from its linked documents. Custom code that writes the same field wins for one save and loses
on the next, because the standard update runs after it. The user sees a status that flips back,
or a document that cannot be cancelled because its status and its log disagree.

## Bad

```python
def mark_delivered(doc, method=None):
    doc.db_set("status", "Delivered")  # the standard status updater overwrites this
```

## Good

```python
# my_app/overrides/delivery_note.py
class CustomDeliveryNote(DeliveryNote):
    def set_status(self, update=False, status=None, update_modified=True):
        super().set_status(update=update, status=status, update_modified=update_modified)
        if self.custom_handover_confirmed and self.status == "To Bill":
            self.status = "Delivered"
            if update:
                self.db_set("status", self.status, update_modified=update_modified)
```

## Find

- `rg -n '\.status\s*=|db_set\(\s*"status"|set_value\([^,]+,[^,]+,\s*"status"' --type py` in the
  app on a doctype the app does not own.
- `rg -n 'docstatus\s*=' --type py`. Only `submit`, `cancel` and `amend` may change `docstatus`.
- `rg -n 'workflow_state' --type py` written outside a workflow transition.
- `rg -n 'doc_events' -A 30 hooks.py` for an `on_update` handler that writes a status.
- `rg -n 'def set_status|def update_status' --type py` in the app with no `super()` call.

## Confirm

A status field on a doctype the app owns end to end has one owner by definition and is not a
finding. Overriding `set_status` and calling `super()` keeps one owner. Writing `docstatus`
directly is always a finding: the framework changes it through `submit`, `cancel` and `amend`,
and each of those runs the matching lifecycle methods. Use the `DocStatus` helpers rather than
the literals 0, 1 and 2 (`source:frappe/model/docstatus.py:DocStatus`).
