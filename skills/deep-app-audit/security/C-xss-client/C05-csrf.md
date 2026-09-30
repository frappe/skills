# C05 — CSRF and unsafe-method semantics

**Scope:** state-changing requests that a third-party page can trigger.

**Why:** a state-changing endpoint reachable without a CSRF token lets any site act as the user.

## Find
- CSRF token generation and validation in the request handler; every code path that skips it
  (`ignore_csrf`, guest requests, API-key auth, webhook routes, OAuth endpoints).
- Whitelisted methods declared with `methods=["GET"]` (or no restriction) that write — a GET
  that mutates is CSRF-able regardless of token handling.
- `allow_guest` endpoints performing writes.
- Cookie attributes: `SameSite`, `Secure`, `HttpOnly` on `sid`.
- Arbitrary URLs accepted into `img src` / link `href` in Desk, which leak or forge requests.

## Confirm
- API-key authenticated requests legitimately skip CSRF; browser-cookie requests must not.
  Verify which branch the endpoint falls into.

## Report
Give the HTML that triggers the request cross-origin.
