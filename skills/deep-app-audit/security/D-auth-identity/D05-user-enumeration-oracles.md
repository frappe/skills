---
id: D05
area: auth-identity
---
# D05 — User enumeration and side-channel oracles

**Scope:** any response that differs based on the existence of a record the caller may not see.

**Why:** login, reset, and signup responses that differ for existing accounts give an
enumeration oracle.

## Find
- Login, signup, password reset, contact/PDDR forms, invite acceptance: compare responses for
  existing vs non-existing accounts (status code, body, redirect, timing).
- The framework-level distinction between `PermissionError` and `DoesNotExistError` — both the
  message and the timing. `get_doc` on a non-existent name vs an unreadable name.
- Link-field search and `validate_link` — do they confirm existence of unreadable records?
- `get_users`, agent lists, mention autocomplete, avatar endpoints.
- Error text that echoes back a doctype or field name the caller cannot read.

## Confirm
- Timing findings need a stated, measurable difference — do not assert one you have not
  reasoned through concretely.

## Report
Low to Moderate; call out anywhere it feeds a higher-severity chain.
