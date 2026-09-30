# I02 — Metadata, system-information, and error leaks

**Scope:** information about the system rather than its records, including what an error tells
the caller.

**Why:** installed apps, translations, and Version records disclose structure, and Version can
expose changes to permlevel'd fields. Stack traces and debug responses in production disclose
paths, queries, and configuration.

## Find — metadata
- Guest-reachable: installed apps and versions, translations, boot info, `/api/method/version`,
  website settings, `robots.txt`/`sitemap` disclosing internal routes, `.json` DocType metadata.
- `frappe.desk.form.load.getdoctype` / `get_meta` — do they expose fields, permissions, and
  custom scripts to users who cannot use the doctype?
- `Version` and `Document Follow` records exposing changes to fields the reader cannot see.
- `Deleted Document`, `Error Log`, `Scheduled Job Log`, `Access Log` read permissions.
- Public catalogue or listing search that reflects internal state.

## Find — errors
- Where tracebacks are serialised into a response: `frappe.local.response`, `exc`,
  `exception` keys, and the conditions under which they are included (`developer_mode`,
  `logging`, `--verbose`).
- `frappe.throw` / `msgprint` messages that embed SQL, file paths, internal doctype names,
  or the value of an internal variable.
- Database error passthrough — a `ProgrammingError` message echoed to the client discloses
  schema and confirms injection.
- 500 pages on portal routes; debug toolbars; `/api/method/frappe.ping`-style diagnostics.
- Whether `developer_mode` can be inferred or toggled from a request.

## Confirm
- Version and framework disclosure alone is Low; pair it with a known CVE to raise it.
- An error leak is a finding only on a path reachable in a production configuration. Say how
  you know it is reachable there.

## Report
State whether the audience is Guest or authenticated. Low on its own; note where it accelerates
another finding.
