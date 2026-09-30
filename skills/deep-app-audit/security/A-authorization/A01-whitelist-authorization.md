---
id: A01
area: authorization
---
# A01 — Whitelisted method authorization

**Scope:** every `@frappe.whitelist()` module-level function that reads or writes a document.
A controller method belongs to `A14`.

**Why:** whitelisting makes a function callable over HTTP; it does not check anything.

This scope is also the largest source of false positives. Most whitelisted functions with no
visible check are guarded by the framework one frame down. Read `_framework-guards.md` sections 1,
2, and 3 before you list anything.

## Find
- `rg -n "@frappe.whitelist" --type py` — build the full inventory first.
- For each, look for a permission check in the body: `frappe.has_permission`,
  `doc.check_permission()`, `frappe.only_for`, `frappe.throw` on a role test.
- Flag any that write through a call that bypasses the document layer, or read through a call
  that applies no permission, with no check.
- With the inventory, start from `.views.unguarded_db_bypass_write` and
  `.views.unguarded_unpermissioned_read`: they leave out the shapes that the framework guards.
  `.views.no_permission_check` does not: most of its entries are guarded by the document layer.
- Look one frame down. A check in the helper that gets the owning record or the parent guards the
  wrapper. `.entry_points[].guard.explicit_checks_in_callees` lists these.

## Confirm
- **Name the write.** `insert()`, `save()`, `submit()`, `cancel()`, `delete()`, and
  `get_mapped_doc()` check permissions themselves, so that endpoint is guarded. The unguarded
  writes are `frappe.db.set_value`, `doc.db_set`, `frappe.db.delete`, raw DML, and any call with
  `ignore_permissions=True`.
- **Name the read.** `frappe.get_list` applies permissions. `frappe.get_all`, each `frappe.db.*`
  read, and `frappe.qb.get_query` by default do not.
- **Name each document at risk.** A check on doctype A does not authorize a read or a write of
  doctype B in the same function. When the document read and the document written are the same,
  and the write goes through the document layer, there is no finding.
- `ignore_permissions=True` anywhere in the path voids the check. Trace it, and trace who sets
  it: a flag that only a scheduled job sets is not reachable from a request.
- The actor must not have the right already: the target doctype does not grant it at permlevel 0
  to an automatic role or to a role of the actor.

## Report
Per the shared format. Group by the doctype being touched, so that triage can route each group.
