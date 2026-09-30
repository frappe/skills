---
id: A14
area: authorization
---
# A14 — Controller methods that write behind a read check

**Scope:** `@frappe.whitelist()` on a method of a DocType controller that writes.

**Why:** a controller method has no URL of its own. `/api/method/run_doc_method` is the usual
route, and it loads the document with `check_permission=True`, which checks **`read`**. So each
write in the method that bypasses the document layer is unguarded for each role that has `read`
but not `write`. A scan for a missing `has_permission` call does not find this: a check runs, but
it is the wrong right.

The same mechanism causes a common false positive. A method on a doctype that only Administrator
can read is not reachable by anybody else (`_framework-guards.md` section 2a). This scope handles
both answers.

## Find
- `.views.doc_method_writing_behind_read_gate` in the inventory is this population.
- By hand: `rg -n -A2 "@frappe.whitelist" --type py`, and keep the hits whose `def` is in a
  `class`. Then keep the methods that write: `self.db_set`, `frappe.db.set_value`,
  `frappe.db.delete`, raw DML, `ignore_permissions=True`, or an `enqueue` of a job that writes.
- A status setter that writes a state field through `db_set` also bypasses the workflow
  transition rules.

## Confirm
State each of these three:

1. **The actor.** The roles that have `read` at permlevel 0 on the owning doctype and do not have
   the right that the write needs (`write`, `submit`, `cancel`, or `delete`). When there are none,
   each user who reaches the method can already do the write, and there is no finding.
2. **The write does not check again.** `self.save()`, `self.submit()`, and `self.cancel()` in the
   method check the right themselves (`_framework-guards.md` section 1). That is not a finding.
   `self.db_set`, `frappe.db.set_value`, and raw DML do not check.
3. **The doctype is reachable.** When only Administrator has `read`, the document load fails
   first. Reject, and say so.

Also check the route. The v2 route (`/api/v2/document/<doctype>/<name>/method/<method>`) checks
`write` for POST. A method that accepts GET is reachable with only `read` on both routes. A call
to the dotted path of the method returns an error: it is not a second entry point.

With a site: the actor with `read` only calls `run_doc_method`, and the document changes. Read the
row back from the database, do not trust the 200. Then show that a user without `read` is
refused.

## Report
Name the owning doctype, the roles that have `read` and not the needed right, the write call that
bypasses the check, and the field that changed. When one doctype has several such methods, report
them as one finding: they are usually one missing check.
