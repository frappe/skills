---
id: B26
area: correctness
---
# B26 — Update every dependent record on rename, cancel and delete

**Why:** A rename changes the primary key. A cancel and a delete end a document's life. Every
record that holds the old name, or that derives its state from the document, must change in the
same transaction. What is left behind is an orphan: a link that points at nothing, a total that
counts a cancelled voucher, or a child row the delete never reached.

## Bad

```python
# my_app/my_app/doctype/route_plan/route_plan.py
class RoutePlan(Document):
    def validate(self):
        ...
    # allow_rename is 1 in the DocType JSON, and Route Stop links to Route Plan by name
```

## Good

```python
class RoutePlan(Document):
    def after_rename(self, old_name, new_name, merge=False):
        frappe.db.set_value(
            "Route Stop", {"route_plan": old_name}, "route_plan", new_name
        )

    def on_trash(self):
        frappe.db.delete("Route Stop", {"route_plan": self.name})
```

## Find

- `rg -n '"allow_rename": 1' --type json` in the app, then check the controller for
  `after_rename`.
- For each doctype the app owns, list the doctypes that link to it, then check the controller
  for `on_trash` and `on_cancel`.
- `rg -n 'def on_cancel' --type py` in the app. A controller with `on_submit` and no `on_cancel`
  is a candidate.
- `rg -n 'ignore_links_on_delete|auto_cancel_exempted_doctypes' hooks.py`. Both switch off a
  guard the framework would otherwise apply.
- `rg -n 'delete_doc\(' --type py` with `force=True` or `ignore_on_trash=True`.

## Confirm

The framework already blocks a delete when a link exists, unless the linked doctype is in
`ignore_links_on_delete`, and it cascades cancel unless the doctype is in
`auto_cancel_exempted_doctypes` (`source:frappe/model/delete_doc.py:check_if_doc_is_linked`).
A link the framework knows about is therefore covered. The finding is a dependency the
framework cannot see: a name stored in a Data field, a Dynamic Link, a cached value, a
workspace, a session, or a row in another system. A doctype with `allow_rename` off cannot be
renamed, so `after_rename` is not needed there.
