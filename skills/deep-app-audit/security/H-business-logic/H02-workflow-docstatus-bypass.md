---
id: H02
area: business-logic
---
# H02 — Workflow and document-state bypass

**Scope:** the submit/cancel/amend lifecycle and workflow transitions.

**Why:** docstatus and workflow state set directly bypass the approval path they represent.

## Find
- Whitelisted helpers that change status directly: `set_status`, `update_status`,
  `set_multiple_status`, `hold`, `resume`, `pause`, `scrap`, `close`, `reopen`, `cancel`.
  Each needs both a permission check and a state-machine check.
- `db.set_value("...", "docstatus", ...)` or `"status"` anywhere — this bypasses validation
  and hooks entirely.
- Workflow transition validation: is the allowed-role check enforced server-side in
  `apply_workflow`, and can a transition be requested out of order?
- `allow_on_submit` fields — are the update-after-submit rules enforced?
- Bulk endpoints that loop over names without re-checking per document.

## Confirm
- Two distinct bugs live here: missing authorization (who) and missing state validation
  (from which state). Report them separately.

## Report
Give the state transition the attacker forces.
