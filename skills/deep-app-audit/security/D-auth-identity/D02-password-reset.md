# D02 — Password reset flow

**Scope:** reset-key generation through password change.

**Why:** a reset token is a password equivalent. Weak generation, missing expiry, or host-header
poisoning of the reset link gives account takeover.

## Find
- Reset key generation: `secrets` vs `random`, length, storage (hashed or plaintext in DB).
- Expiry, single-use enforcement, invalidation on use and on a second request.
- The link's host: is it built from `Host` / `X-Forwarded-Host` (poisoning) or from
  configured `host_name`?
- Response differences between a known and unknown email — cross-reference `D05`.
- Rate limiting on the request endpoint — cross-reference `A04`.
- Whether reset completes 2FA-independently (a reset that bypasses 2FA is a finding).
- Whether sessions and API keys are invalidated after a reset.

## Confirm
- Read the actual key comparison — a non-constant-time compare on a reset key is exploitable
  only in theory here, but a missing expiry is exploitable today.

## Report
Order findings by how much attacker knowledge each needs.
