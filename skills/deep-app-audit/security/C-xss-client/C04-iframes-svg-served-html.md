# C04 — Untrusted iframes, SVG, and served HTML

**Scope:** content executed in the app's origin because of how it is embedded or served.

**Why:** iframes, uploaded SVG, and HTML served from the site origin all execute in that origin.

## Find
- `<iframe srcdoc=` and `<iframe src=` with a data or blob URL — email bodies, print previews,
  builder previews. Check for `sandbox` attributes.
- Uploaded SVG served with `image/svg+xml` from the site origin — SVG executes script.
- Any route serving user-uploaded HTML, or nginx serving `/files/*.html` inline.
- `Content-Type` and `Content-Disposition` on file download routes; `X-Content-Type-Options`.
- `postMessage` handlers without an origin check.

## Confirm
- Same-origin serving is what makes this critical; a separate cookieless domain neutralises it.
  Check which the deployment uses.

## Report
State the origin the payload executes in.
