---
id: D07
area: auth-identity
---
# D07 — API key and token handling

**Scope:** non-session credentials.

**Why:** API keys and tokens must be stored and transmitted as secrets, not as ordinary fields.

## Find
- API secret generation, storage (must be in the encrypted password store, not a Data field),
  and whether it is ever returned after creation.
- Who can generate or read another user's API key — `generate_keys` and its permission check.
- Tokens in query strings, logs, Error Log tracebacks, or realtime payloads.
- `Authorization: token` handling: constant-time compare, rate limiting on failures.
- Whether API-key auth bypasses 2FA, IP restriction, or session expiry, and whether that is
  intended.
- Token revocation on password reset, user disable, and role removal.

## Confirm
- A key readable by a System Manager for another user may be intended; a key readable by a
  peer user is not.

## Report
State the credential's blast radius.
