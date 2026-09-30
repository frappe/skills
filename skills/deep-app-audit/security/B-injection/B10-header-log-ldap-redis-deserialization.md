---
id: B10
area: injection
---
# B10 — Header, log, LDAP, Redis injection and unsafe deserialization

**Scope:** the remaining injection sinks, grouped because each is individually rare here.

**Why:** OWASP gap coverage. A header parser that mishandles an edge case can make the app
trust a forged identity.

## Find
- **Response/CRLF:** user input into `frappe.local.response.headers`, `Content-Disposition`
  filenames, redirect `Location`, cookie values.
- **Email headers:** recipient, subject, `Reply-To`, `Message-ID` built from user input;
  encoded-word and address-parsing edge cases on inbound mail.
- **Logs:** CRLF or newline in values written to application logs — an attacker forging log
  lines. User input used as a log key, a logger name, or a filename
  (`frappe.logger(<user input>)`), which is also a path-traversal sink, cross-reference `E01`.
  Log entries carrying secrets or PII belong to `G02`; hand those cases there.
- **LDAP:** `ldap` search filters built by concatenation in the LDAP auth integration.
- **Redis:** cache keys built from user input (namespace escape, key collision), and any
  `redis.execute_command` with user data.
- **Deserialization:** `rg -n "pickle|marshal|yaml\.load\(|jsonpickle|dill|shelve" --type py`
  — flag `yaml.load` without `SafeLoader`, and any `pickle.loads` on stored or request data.

## Confirm
- For Redis, a cache-key collision that lets one user read another's cached value is a real
  finding; a merely ugly key is not.
- For logs, show the injected line as it would appear. Log forging is Low to Moderate; raise it
  where it can erase evidence.

## Report
Separate by sub-sink so triage can route them.
