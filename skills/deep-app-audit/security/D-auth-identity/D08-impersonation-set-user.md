---
id: D08
area: auth-identity
---
# D08 — Impersonation and `set_user`

**Scope:** code that changes the acting identity, and data that records an author.

**Why:** `set_user` and author fields such as `raised_by` let a caller act as another user.

## Find
- `rg -n "frappe\.set_user|set_user_lang|frappe\.session\.user\s*=" --type py` — for each,
  is the target identity request-controlled, and is the original user restored in a `finally`?
- Impersonation features (support/admin "log in as") — authorization, audit log, time limit.
- Author fields written from the request rather than the session: comment `owner`, Communication
  `sender`, ticket `raised_by`, `contact_email`, Lead source, `modified_by`.
- Background jobs that inherit or set a user — `enqueue(..., user=...)`.

## Confirm
- A `set_user` without restoration corrupts the rest of the request, which can turn a
  read-only endpoint into a privileged one. Trace what runs after it.

## Report
Separate "acts as another user" from "claims to be another user" — different severities.
