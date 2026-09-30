# D03 — Two-factor authentication

**Scope:** 2FA enrolment, verification, recovery, and the controls that claim to complement it.

**Why:** 2FA fails when an IP check trusts a spoofed `X-Forwarded-For`, and when a path skips
the second factor.

## Find
- The state between password verification and OTP verification: what is the temporary token,
  can it be replayed, does it already grant a session?
- OTP validation: window size, single use, brute-force limit, constant-time compare.
- Recovery codes: generation, storage, single use.
- Whether 2FA can be disabled, or a reset link issued, by an actor who only has the password.
- IP restriction / `restrict_ip` logic: does it trust `X-Forwarded-For` or `X-Real-IP` without
  a trusted-proxy allowlist? That defeats both 2FA and IP restriction.
- Endpoints reachable *before* 2FA completes.

## Confirm
- Enumerate every authenticated entry point (API key, OAuth token, webhook) and check whether
  it is subject to 2FA at all. An API key that skips 2FA may be intended — say so explicitly.

## Report
Critical if a password alone yields a session.
