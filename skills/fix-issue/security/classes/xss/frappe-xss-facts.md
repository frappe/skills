# What Frappe's sinks and filters actually do

Read on `frappe` `develop` in October 2026. The same helpers exist on `version-15` and `version-16`.
Function names are stable. Line numbers drift, so search by name. Re-read the source in your own
bench before relying on any row — a fact about the framework is only as current as the checkout.

## Sinks — all raw

| Sink | Behaviour | Source |
|---|---|---|
| Server Jinja | `SandboxedEnvironment` with no `autoescape`: `{{ x }}` emits raw HTML | `frappe/utils/jinja.py` (`get_jenv`) |
| Desk microtemplate (`public/js/**/templates/*.html`, JS `frappe.render_template`) | `{{ x }}` is rewritten to `{%= x %}`, a raw push | `frappe/public/js/frappe/microtemplate.js` |
| `__("… {0}", [v])` | substitutes with `$.format`. `v` is not escaped | `frappe/public/js/frappe/translate.js` |
| `frappe.msgprint` / `frappe.throw` (JS) | inserted with `.html()` | `frappe/public/js/frappe/ui/messages.js` |
| `frappe.utils.get_form_link(dt, name, html, display_text)` (JS) | encodes the name and escapes the *default* display text. A `display_text` you pass is **not** escaped | `frappe/public/js/frappe/utils/utils.js` |

## Encoders

| Helper | Behaviour |
|---|---|
| `frappe.utils.escape_html` (Py, `frappe/utils/data.py`) | escapes `& " ' < >` |
| `frappe.utils.escape_html` (JS, `utils/utils.js`) | escapes `& < > " ' \` =`; returns `""` for null |
| `frappe.utils.bold` (JS) / `frappe.bold` (Py) | escapes, then wraps in `<strong>` |
| `frappe.utils.html_utils.sanitize_html` | allowlist HTML cleaner — for rich text only |
| `frappe.utils.html_utils.clean_html`, `clean_email_html` | smaller allowlists |
| `frappe.utils.sanitise_redirect` (JS, `utils/common.js`) | returns `""` for a cross-origin URL |

## Filters that look like protection and are not

- **`sanitize_html` returns its input unchanged when it contains no complete tag.** Its test is a
  regex for `<[a-zA-Z][^>]*>`, so `<img src=x onerror=alert(1)` with no closing `>` passes through
  (`html_utils.py`, `has_html_tags`).
- **The save-time filter (`BaseDocument._sanitize_content`) skips any value with no `<` or `>`**, so
  an attribute breakout like `x" onerror="…"` always reaches the database. It also skips `Attach`,
  `Attach Image`, `Barcode`, `Code`, `JSON`, Email-option fields and fields marked
  `ignore_xss_filter` — and `Attach Image` values land in `src=`.
- **Guest requests** to a method not marked `xss_safe` get `sanitize_html_payload` on `form_dict`
  strings, and inherit the same unterminated-tag gap.
- **JS `frappe.utils.xss_sanitise`** regex-strips `<script>` and `alert(`. Its own comment says it
  does not handle event handlers.
- **The legacy global JS `escape()`** is URL percent-encoding. `data-x="{{ escape(v) }}"` in old
  templates is not HTML escaping.
- **Record names may contain `"`.** Name validation blocks angle brackets, not quotes, so a document
  name is attacker-controlled attribute content.

## Pitfalls

1. **An unchanged sink proves nothing.** A fix can escape the value on the one hop where it is
   copied into a staff-visible record, and leave both the entry point and the sink template
   untouched. Measure the stored value.
2. **Fixing one argument is not fixing the endpoint.** When an endpoint stores several
   caller-supplied fields, the incomplete patch escapes the obvious one and leaves its siblings raw.
3. **Double escaping cuts both ways.** Moving the escape into the Python response without removing
   the template-side escape shows `&amp;quot;` to users. "Fixing" that by deleting the escape
   entirely reopens the hole. Check the value is escaped exactly once.
4. **Escaping in a Python response changes the API.** A REST consumer then receives `&quot;`. Do it
   only for responses that feed HTML alone.
5. **Partial backports are common.** A template can carry all of its escapes on one release line and
   only some on another. Read the template at each release tag. See
   [verify.md](../../verify.md).
6. **Realtime pushes are sinks too.** A `publish_realtime` that broadcasts the value can reach users
   who could never open the page.
