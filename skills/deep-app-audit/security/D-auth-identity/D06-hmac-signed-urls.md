---
id: D06
area: auth-identity
---
# D06 — HMAC, signed URLs, and verified commands

**Scope:** requests authenticated by a signature rather than a session.

**Why:** signed URL schemes fail through missing expiry, a weak or shared secret, and
non-constant-time comparison.

## Find
- `verified_command`, `get_signed_params`, `verify_request`, `validate_signature`, webhook
  signature verification (inbound and outbound).
- For each: is the signing secret genuinely secret and per-site? Is it derived from something
  guessable?
- Does the link expire? Is it single-use?
- Parameters outside the signature: does the handler read any value that the signature does
  not cover, such as a form field added to a signed URL? Check every verified endpoint for
  parameters not covered by the signature.
- Signature comparison: `hmac.compare_digest` or `==`?
- Signature algorithm and whether the payload is length-delimited (canonicalisation).

## Confirm
- Show which parameter is unsigned and what changing it achieves.

## Report
High by default — these endpoints usually act with elevated privilege.
