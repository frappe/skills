---
id: A35
area: customization
mechanism: M30
---
# A35 — `ignore_links_on_delete` and `auto_cancel_exempted_doctypes` are for log-like DocTypes

**Why:** Both hooks are global lists that merge across every installed app. Adding a
transactional DocType turns off the link check for the whole bench. A user then deletes a
document that other documents still reference, and the references point at nothing.

## Bad

```python
# my_app/hooks.py
ignore_links_on_delete = ["Sales Invoice", "Permit", "Permit Application"]
auto_cancel_exempted_doctypes = ["Sales Order"]
```

## Good

```python
# my_app/hooks.py
ignore_links_on_delete = ["Permit Sync Log", "Permit Request Log"]
```

## Find

- `rg -n 'ignore_links_on_delete|auto_cancel_exempted_doctypes' hooks.py`.
- For each named DocType, read its JSON: `is_submittable`, the number of Link fields that point
  at it, and whether any standard DocType links to it.
- A DocType the app does not own in either list is a strong finding.

## Confirm

`delete_doc` consults `ignore_links_on_delete` in three places to skip the link check
(`frappe/model/delete_doc.py`). The list merges across apps, so an entry affects every app.

A log DocType has these marks: it is not submittable, nothing links to it, it holds a reference
to another document rather than the other way round, and losing a row loses no business meaning.

`auto_cancel_exempted_doctypes` stops the cascade that cancels linked documents. That is correct
for a log and wrong for a transaction, because a cancelled document then keeps live children.

A DocType from another app in either list is a finding even when the entry looks harmless, because
the other app owns that decision.
