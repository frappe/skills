---
id: A07
area: authorization
---
# A07 — Child table and linked-doctype permission

**Scope:** reaching a parent document through a child row, or through dot-notation fields.

**Why:** child tables and Link fields inherit permission from the parent only when the code asks
for it. Direct access to the child doctype bypasses the parent check.

## Find
- API calls where `doctype` is a child doctype (`istable: 1`) — check whether parent
  permission is enforced.
- `fields` parameters containing a dot: `customer.tax_id`, `link_field.secret`. These join
  to another table; confirm the joined doctype's permission is checked, not just the base.
- `frappe.get_all` with `parent=` supplied from the request.
- Report and list-view `group_by` on linked fields.

## Confirm
- The test is simple: can an actor with read on doctype A read a field of doctype B where
  they have no read on B?
- A child table has no permission rows of its own. The parent authorizes it. An empty
  `permissions` array on a child table is normal, not a finding. The finding is a query that
  reads a child doctype without a check on its parent.
- The child row's parent is found and checked on the parent doctype: guarded.
- The actor has `read` at permlevel 0 on the linked doctype, or an automatic role has it: no
  boundary is crossed.

## Report
Give the exact `fields` payload that leaks the linked value, and name the parent doctype whose
permission was not checked.
