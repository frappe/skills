---
id: A08
area: authorization
---
# A08 — Privilege escalation paths

**Scope:** any path from a lower role to a higher one.

**Why:** a user who can write to role, permission, or user records can grant themselves
anything.

## Find
- Endpoints that write to `Has Role`, `User`, `Role Profile`, `User Permission`, or set
  `user_type`.
- Invite / onboarding flows that accept a role from the request.
- Content authored by a low role and executed in a high role's browser or server context:
  Client Script, Form Script, Print Format (Jinja), Web Page script, Notification message,
  Dashboard Chart source, Server Script.
- Arbitrary DocType creation or `Custom Field` / `Property Setter` writes by a non-admin —
  these are RCE-adjacent in Frappe.
- `frappe.set_user` / `set_user_lang` reachable from a request.

## Confirm
- Ask which role authors the artefact and which role's session executes it. A mismatch in the
  upward direction is the finding.

## Report
State the start role, the end role, and the shortest chain between them.
