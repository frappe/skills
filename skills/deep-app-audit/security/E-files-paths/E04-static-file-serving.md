---
id: E04
area: files-paths
---
# E04 — Static file serving

**Scope:** how the web server and the app hand out files.

**Why:** nginx serving private files directly bypasses every application check.

## Find
- nginx config wherever your deployment generates it (bench, a provisioning tool, or a hand-written
  template), if you have access to it: `location /files`, `location /private`,
  `X-Accel-Redirect` usage, and whether `/private/` can be reached directly.
- The app-side handler that issues `X-Accel-Redirect` — does it check permission before
  setting the header?
- `Content-Type` inference for served files, and whether HTML/SVG are served inline.
- Directory listing, and access to `site_config.json`, backups (`/private/backups`), and
  `.git` from the web root.
- Asset paths (`/assets/`) serving anything user-writable.

## Confirm
- This scope straddles the app and the deployment. Report app-side findings here and mark
  nginx-config findings as deployment issues so they route to the right team.

## Report
URL, expected access, actual access.
