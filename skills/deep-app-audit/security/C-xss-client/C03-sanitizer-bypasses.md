# C03 — Sanitizer bypasses

**Scope:** the sanitisation helpers themselves.

**Why:** sanitizer configuration decides whether stored HTML is safe, and a sanitizer that
matches patterns is easy to bypass.

## Find
- `remove_script_and_style`, `sanitize_html`, `strip_html`, `is_html`, `html2text`,
  `escape_html`, `clean_html`, markdown renderers, `frappe.utils.md_to_html`.
- Client-side equivalents and any DOMPurify config with `ALLOWED_TAGS`/`ADD_ATTR` overrides.
- `msgprint` / `frappe.throw` with HTML in the message, and translated strings with
  interpolation.
- The `ignore_xss_filter` flag on DocFields — enumerate every field that sets it.

## Confirm
- Regex-based tag stripping is bypassable almost by definition — look for nested or malformed
  tags, `<svg>`/`<math>` namespaces, event handlers on allowed tags, `javascript:` and
  `data:` URLs on allowed attributes, and mXSS via mutation on reparse.
- Test the bypass against the code in this checkout.

## Report
Include the exact bypassing input.
