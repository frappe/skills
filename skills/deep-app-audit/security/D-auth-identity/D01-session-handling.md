# D01 — Login and session handling

**Scope:** session creation, storage, transport, and destruction.

**Why:** session fixation, missing invalidation, and cookie flags decide whether a leaked
session stays usable.

## Find
- Session ID generation: source of randomness, length, and whether it is regenerated on
  privilege change (login, 2FA completion, impersonation stop).
- `sid` appearing in URLs, redirects, referrers, logs, or emails — login-with-URL flows should
  issue a one-time token, not a reusable SID.
- Cookie flags on `sid` and `user_id`: `HttpOnly`, `Secure`, `SameSite`.
- Session expiry: idle timeout, absolute timeout, `Session Expiry` setting enforcement
  server-side, and whether expiry actually deletes the server-side session.
- Logout: does it invalidate the server-side session for all devices where intended?
- Concurrent session limits and device tracking, if the app claims to have them.

## Confirm
- A session that survives a password change or a 2FA reset is a finding.

## Report
State the exact reuse window.
