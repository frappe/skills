# F01 — Server-Side Request Forgery and outbound TLS

**Scope:** outbound connections where the destination is influenced by a request, or where
certificate validation is off.

**Why:** an outbound request with a request-controlled URL reaches internal services. Server
Scripts and integration settings are the common entry points. Outbound TLS with verification
disabled makes every integration interceptable.

Both questions read the same outbound call sites, so they are one scope.

## Find — destination
- `rg -n "requests\.|urllib|httpx|urlopen|make_get_request|make_post_request|make_request" --type py`
  and check the URL argument's origin.
- Frappe-specific sinks: `convert_to_webp` / image fetch by URL, `report_to_pdf` and any
  wkhtmltopdf/Chrome rendering of user HTML (external resources in the HTML are the SSRF),
  webhook target URLs, OAuth/OIDC discovery URLs, Currency Exchange and other integration
  settings, Data Import from URL, avatar/logo fetch, LDAP host, SMTP/IMAP host.
- HTTP utilities exposed inside the template or Server Script sandbox — cross-reference `B06`
  and `B07`.

## Find — TLS verification
- `rg -n "verify\s*=\s*False|ssl\._create_unverified|CERT_NONE|check_hostname\s*=\s*False|InsecureRequestWarning" --type py`
- Email: SMTP/IMAP/POP connection setup — `starttls` without context verification, or
  `SSL_CONTEXT` built without `check_hostname`.
- Any integration that disables verification behind a settings flag, and who can set the flag.

## Confirm
- Ask what the attacker reaches: cloud metadata (169.254.169.254), internal services
  (redis:6379, mariadb:3306, a deployment or provisioning API), or localhost admin endpoints. Name one.
- Check for redirect following — a validated URL that then 302s internally is still SSRF.
- Blind SSRF still counts; state the oracle (timing, error text, rendered content).
- A verification flag that defaults to safe but that a low-privilege role can set is a finding
  in its own right. Name the protocol and what transits the connection.

## Report
Critical where cloud metadata or an internal admin API is reachable.
