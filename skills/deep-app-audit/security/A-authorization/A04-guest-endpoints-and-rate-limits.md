---
id: A04
area: authorization
---
# A04 — Guest endpoint surface and rate limiting

**Scope:** every unauthenticated endpoint in the app, and the abuse limits on the endpoints an
attacker can call repeatedly.

**Why:** `allow_guest=True` is not an escape hatch. It removes authentication from everything
the function can reach, so the whole reachable path must be safe for an anonymous caller. An
unauthenticated endpoint without a rate limit is then abused for SMS and mail cost, and for
brute force.

Both questions read the same inventory, so they are one scope: build the guest surface once,
then ask of each endpoint what it exposes and what it costs.

## Find — the guest surface
- `rg -n "allow_guest\s*=\s*True" --type py`
- Portal routes and `website_route_rules` in `hooks.py`.
- `has_website_permission` hooks and web-form guest submission paths.
- `frappe.set_user("Administrator")` or `ignore_permissions` inside any guest path — treat as
  critical until proven otherwise.

Per endpoint, answer:
1. Is it genuinely meant to be public?
2. Does it authenticate the request some other way (HMAC, signed token, webhook signature)?
3. Does the response contain only what the public purpose requires?
4. Can it write anything?

## Find — abuse limits
- Take the guest inventory above and ask of each: what does calling it 10,000 times cost the site owner?
- The named-risk set, guest or not: login, password reset, OTP/SMS send, signup,
  contact/feedback forms, file upload, search, email send, invite acceptance, coupon
  redemption.
- `frappe.rate_limiter` / `@rate_limit` usage — which endpoints have it, what the limits are,
  and what the key is (IP? session? user?). An IP-keyed limit behind a proxy that trusts
  `X-Forwarded-For` is no limit at all — cross-reference `F02`.
- Account lockout on repeated failed logins, and whether lockout is itself a DoS on the victim.

## Confirm
- A guest endpoint that returns a document is a finding unless the doctype is published
  content and the query filters on the published flag server-side.
- Distinguish a missing limit (finding) from a limit set too high (note).

## Report
Produce the full guest inventory even where clean. It is the list a reviewer stores as the
baseline for the invariant-diff check `P02`, which rebuilds it independently. For each limit
gap: endpoint, cost per call, current limit.
