---
id: F02
area: ssrf-outbound
---
# F02 — Trusting client-supplied headers

**Scope:** `Host`, `Origin`, `Referer`, `X-Forwarded-For`, `X-Forwarded-Host`, `X-Real-IP`.

**Why:** `Origin`, `Host`, and `X-Forwarded-For` are attacker-controlled. They poison generated
URLs and defeat IP restrictions.

## Find
- `rg -n "get_url\(|request\.host|HTTP_HOST|X-Forwarded|Origin|Referer|remote_addr" --type py -i`
- Every use of `frappe.utils.get_url` in a context that produces a link sent to a user
  (password reset, invite, verification, notification, webhook callback).
- IP-based controls: `restrict_ip`, rate limiting, audit logging, geo checks — do they read
  a forwarded header without a trusted-proxy allowlist and hop count?
- CORS handling: is `Origin` reflected? Is `Allow-Credentials` set with a reflected origin?

## Confirm
- The mitigation is a configured `host_name` / trusted-proxy list, not header sanitisation.
  Check whether the config exists and is actually consulted.

## Report
State what the spoofed header buys: a poisoned link, a bypassed control, or a leaked secret.
