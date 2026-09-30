# A05 — Role and permission model drift

**Scope:** DocType permission JSON and role definitions, not Python.

**Why:** roles and permission rules drift as features are added. A role that looks narrow in the
UI often carries wide document permissions.

## Find
- Every `*.json` DocType file: permissions granted to `All`, `Guest`, `Website User`,
  `Customer`, `Supplier`, or a portal-facing role.
- `"select": 1` without `"read": 1` — in Frappe these have historically been equivalent, so
  treat a Select grant as a Read grant and judge it that way.
- Fields with `permlevel > 0` and whether any permission row actually restricts that level.
- Roles with `desk_access: 1` that are assigned to external parties.
- `if_owner` rows — check the doctype actually has a meaningful `owner`.
- Default role on signup, and roles auto-assigned by portal onboarding.

## Confirm
- Read the doctype's fields before judging. A permission on a metadata doctype is not the
  same risk as one on a transactional doctype with PII or money.

## Report
One line per over-broad grant, with the sensitive fields it exposes.
