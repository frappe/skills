# D04 — OAuth 2.0 / OIDC / SSO

**Scope:** the app as OAuth provider and as OAuth client.

**Why:** OAuth and SSO fail through dynamic client registration, open redirect via `state`, and
email-only account linking.

## Find
- **As provider:** `redirect_uri` validation (exact match vs prefix vs substring), dynamic
  client registration and whether it is open, scope enforcement, `introspect_token` access
  control, refresh-token rotation and revocation, PKCE support and enforcement, authorization
  code single-use and binding to the client.
- **As client:** `state` generation and verification, nonce for OIDC, ID-token signature and
  issuer/audience validation, and — the recurring bug — whether an account is linked by email
  address alone without verifying the provider asserts that email.
- Any place a token or code appears in a URL, log, or referrer.

## Confirm
- Email-only linking is an unauthenticated account takeover when any provider can assert an
  arbitrary email. State which provider makes it exploitable.

## Report
Split provider-side and client-side findings.
