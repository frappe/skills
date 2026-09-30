---
id: A01
area: authorization
---
# A01 — Whitelisted method authorization

**Scope:** every `@frappe.whitelist()` function that reads or writes a document.

**Why:** whitelisting makes a function callable over HTTP; it does not check anything.

## Find
- `rg -n "@frappe.whitelist" --type py` — build the full inventory first.
- For each, look for a permission check in the body: `frappe.has_permission`,
  `doc.check_permission()`, `frappe.only_for`, `frappe.throw` on a role test.
- Flag any that call `frappe.get_doc`, `frappe.db.get_value`, `frappe.db.set_value`,
  `doc.save()`, `doc.submit()`, `doc.delete()`, or `frappe.new_doc` with no check.

## Confirm
- `frappe.get_doc(...).save()` does run permission checks; `db.set_value` and
  `db.sql` do not. Know which sink you are looking at.
- A check on doctype A does not authorize a write to doctype B in the same function.
- `ignore_permissions=True` anywhere in the path voids the check — trace it.

## Report
Per the shared format. Group by the doctype being touched, so that triage can route each group.
