---
id: L02
area: supply-chain
---
# L02 — JavaScript dependency CVEs

**Scope:** every `package.json`, lockfile, and vendored JS file in the repo, frontend and
server-side alike.

**Why:** old pinned frontend libraries, such as UI toolkits, rich-text editors, and JavaScript
sandboxes, carry known XSS and sandbox escape bugs.

## Find
- Enumerate all `package.json` files, including `packages/*`, app frontends, and the socketio
  service.
- Run the available audit tool (`yarn npm audit`, `npm audit --json`) against the lockfile and
  report only what the lockfile actually resolves to.
- Vendored JS committed under `public/js/lib`, `public/vendor`, or similar — audit these
  manually. They are invisible to tooling and are typically the oldest code in the repo.
- Separate browser-shipped code from build-time-only tooling.
- Note packages that are unmaintained, or where the fixed version is a major bump.

## Confirm
- The socketio service runs server-side JS — treat its CVEs at server severity, not client.
- A prototype-pollution or XSS CVE in a library the app does not use that way is informational.
  State whether the vulnerable code path is actually used.
- A dev-only build tool CVE is informational.

## Report
Same table as `L01`, plus "ships to browser / runs on server / build only".
