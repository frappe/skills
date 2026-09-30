---
id: A05
area: authorization
---
# A05 — Role and permission model drift

**Scope:** DocType permission JSON and role definitions, not Python.

**Why:** roles and permission rules drift as features are added. A role that looks narrow in the
UI often carries wide document permissions.

Read `_framework-guards.md` section 6 first. Each rule below has made a published role gap wrong.

## Find
- Every `*.json` DocType file: permissions granted at **permlevel 0** to `All`, `Guest`,
  `Website User`, or a role that the app gives to external parties. Which roles are external is
  different in each app: read the roles of the app, and its signup and portal onboarding paths.
- A grant to an automatic role (`All`, `Guest`, `Desk User`) on a doctype that holds sensitive
  data. Nobody grants these roles, so each user of the matching type has the right. `All`
  includes Website Users. This is the finding class of this scope: one finding for the grant,
  not one for each endpoint that reads the doctype.
- `"select": 1` without `"read": 1`. This is a deliberate grant: the user can pick the record in a
  Link field and see it in search results, and cannot open it. Link and search queries check
  `select`, and document loads check `read`. Judge each on its own right. A `select` grant is a
  finding only when the fields that search shows (the title field and the search fields) are
  sensitive.
- Fields with `permlevel > 0`, and whether a permission row restricts that level. Levels above 0
  control fields, never whether a document opens. A role that appears only at permlevel 1 cannot
  read the document.
- Roles with `desk_access: 1` that are assigned to external parties.
- `if_owner` rows — check the doctype actually has a meaningful `owner`.
- Default role on signup, and roles auto-assigned by portal onboarding.

## Confirm
- Read the doctype's fields before judging. A permission on a metadata doctype is not the
  same risk as one on a transactional doctype with PII or money.
- A child table (`istable: 1`) has no permission rows. The parent authorizes it. An empty
  `permissions` array on a child table is normal, not "Administrator only", and not a finding.
- A role gap is real only when, at permlevel 0 and on the right that the endpoint checks, the
  role that reaches the endpoint does not hold the right, and no automatic role of that user
  holds it. State all three parts.
- With a test site, read the live rows. A `Custom DocPerm` row replaces the stock rows of its
  doctype.

## Report
One line per over-broad grant, with the permlevel, the right, and the sensitive fields it exposes.
