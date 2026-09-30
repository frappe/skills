---
id: P03
---
# P03 — Clickjacking, CSP, and security headers

**Kind:** posture check. A missing header is a gap in the response, not a reachable defect, so
it produces a table rather than findings.

## Task
- Find where headers are set: request handler, `hooks.py`, nginx templates, `website_context`.
- Check for: `Content-Security-Policy` (and whether it allows `unsafe-inline`/`unsafe-eval`,
  which Desk historically needs — record the gap), `X-Frame-Options` or CSP `frame-ancestors`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Strict-Transport-Security`,
  `Permissions-Policy`.
- Check whether these apply to portal pages, `/api` responses, and file downloads alike.
- Find any code path that lets a document field influence a header (`allow_iframe` style
  settings).

## Confirm
- A missing header on its own is Low. If you can pair it with a concrete attack — clickjacking
  a state-changing portal action, sniffing an uploaded file into HTML — report that attack as a
  finding in its own right and say which scope it belongs to.

## Output
One table: header, current value, gap. Mark each row app-level or deployment-level so it routes
to the right team.
