# Fix XSS in a Frappe app

**In Frappe every sink is raw.** Nothing escapes for you: not the desk microtemplate, not Jinja
(no autoescape), not `__()` arguments, not `msgprint`/`frappe.throw`, not `$(html)`. The save-time
XSS filter is a markup filter, not an escaper, and it misses most real payloads (see
[the facts](xss/frappe-xss-facts.md)). So the fix is always an **encoder at the sink, chosen
by context**, applied right before the value enters the DOM or the template.

## Steps

### 1. Trace every hop, not just the sink

List the **entry** (who can write the value: a role's form, REST `POST /api/resource`, an
`allow_guest` endpoint, an import), the **storage** (which field, which doctype, any copy into
another record), and every **sink** that renders it (form, list, report formatter, page, dashboard,
portal page, print format, email, timeline, realtime push).

Done when: each hop names a file and line. A finding naming three locations is unfixed only if all
three were read — a fix at the middle hop (escape on copy) leaves the entry and sink unchanged and
still closes it.

### 2. Pick the encoder by context

| The value lands in | Encoder |
|---|---|
| HTML text or a quoted attribute other than a URL, in JS | `frappe.utils.escape_html(v)` |
| HTML text or a quoted attribute other than a URL, in Jinja | `{{ v \| e }}` |
| A URL attribute (`href`, `src`, `action`) | allow only the schemes the feature needs, usually `http`, `https` or a relative path, and refuse the rest; then escape it as an attribute. Escaping alone leaves `javascript:alert(1)` working |
| A desk link to a record | `frappe.utils.get_form_link(doctype, name)` for the `href` — it `encodeURIComponent`s the name — and `escape_html` on the display text |
| A URL path segment | `encodeURIComponent(v)` |
| A jQuery selector | `$.escapeSelector(v)` |
| Bold text in a message | `frappe.utils.bold(v)` (JS) / `frappe.bold(v)` (Py) — both escape first |
| An argument to `__()` / `_()` that ends up in `msgprint`/`throw` | escape each argument **before** it enters `__()` |
| Jinja inside a `<script>` | `{{ v \| tojson }}` |
| A rich-text field meant to carry formatting | `frappe.utils.html_utils.sanitize_html(v)` (`{{ frappe.sanitize_html(v) }}` in Jinja) — for content, while attributes take `escape_html` |
| A table cell built with jQuery | `$("<td>").text(v)` beats string-building |

Replace the legacy global JS `escape()` wherever you meet it: it is URL percent-encoding, not HTML
escaping. Use the encoders above in place of `frappe.utils.xss_sanitise`, whose own source says it
does not handle event handlers.

Done when: every interpolation of a non-constant value in the touched sinks goes through an encoder
matching its context. Count them. A partial fix that escapes 5 of 8 values in one template is the
common failure.

### 3. Escape at the sink, and only there

Put the encoder **at the sink**, right before the value enters the DOM or the template. Do not fix
XSS upstream:

- **Do not escape at storage or in a Python response.** The stored value then differs from what the
  user typed, every REST consumer receives `&quot;`, rows stored before the fix stay raw, and a sink
  added later trusts a value that only looks safe.
- **Do not strip or reject special characters.** A name may legitimately hold `&`, `"` or `<`.
  Removing them corrupts data and still misses the payloads that need none of them.

The one exception is a field that is meant to hold markup: give it the allowlist sanitizer
(`sanitize_html`, or a `Text Editor` field, which frappe sanitizes) and escape its attributes as
usual.

If the fix you backport escapes upstream, do not copy that shape. Write the sink escape on this
branch, and report the difference.

Done when: each value is escaped exactly once, at each sink — not zero, not twice.

### 4. Verify with payloads that defeat the filter

Store each payload through the real API as the **lowest role that can write the field** (or as Guest
on an `allow_guest` path), read it back from the database, then open every sink as the **victim**
(the most privileged role that renders it — often System Manager). Use the payload sets of
[verify.md](../verify.md):

- **control**: the brief's payload. It must fire on the pre-fix code.
- **probes**:
  - `x" onmouseover="alert(document.domain)` — attribute breakout. No `<>`, so the save filter never
    sees it. Record names may contain `"`.
  - `<img src=x onerror=alert(1) ` — an unterminated tag passes `sanitize_html` unchanged.
  - `<img src=x onerror=alert(1)>` — the save filter strips this one on the fields it covers. When
    it is stripped before the fix, note that as the reason, not as a failure.
  - `javascript:alert(1)` — in any URL or link field.
  - `</script><script>alert(1)</script>` — for Jinja inside a script block.
- **allowed calls**: a value with `&`, `"` and `<` in it, which must display exactly as typed, and
  formatted content in a rich-text field, which must keep its formatting.

Inspect the **live DOM**, because microtemplates render client side.

Done when, on the branch, at every sink from step 1: the control fired before the fix,
every probe renders inert after it, and every allowed call displays the same as before.

Template injection (`{{ }}` evaluated server side) is a different class:
[classes/template-code-injection.md](template-code-injection.md).
Shipping, backports and the public PR: [the security workflow](../workflow.md).

## References

- [frappe-xss-facts.md](xss/frappe-xss-facts.md) — what each Frappe sink and filter really
  does, with source locations. Read before arguing that something "is already escaped".
