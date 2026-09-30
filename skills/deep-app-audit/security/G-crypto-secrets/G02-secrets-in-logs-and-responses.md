---
id: G02
area: crypto-secrets
---
# G02 — Secrets in logs, errors, and responses

**Scope:** accidental egress of credentials.

**Why:** a key returned to authenticated users or written to a log is disclosed to everyone who
can read it.

## Find
- `frappe.log_error`, `frappe.logger()`, `print`, and traceback capture — do any of them
  serialise a request body, a doc with a password field, or an integration settings object?
- `Error Log` and `Integration Request` doctypes: what do they store, who can read them, and
  is the payload redacted?
- `frappe.boot` and `website_context` — enumerate every key; a secret in boot info reaches every
  logged-in user.
- Client-visible settings singles: which fields ship to the browser?
- Request logging (nginx, gunicorn) capturing query strings that contain tokens.
- `as_dict()` / `as_json()` on documents with password fields in an API response.

## Confirm
- Check `Error Log` read permission specifically — it is often broader than expected.

## Report
Name the credential and the audience it reaches.
