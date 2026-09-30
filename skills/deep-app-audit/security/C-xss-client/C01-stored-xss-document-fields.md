---
id: C01
area: xss-client
---
# C01 — Stored XSS via document fields

**Scope:** field values written by one user and rendered as HTML for another.

**Why:** document fields render in the desk and on portal pages, so a stored payload runs for
every later viewer.

## Find
- Fieldtypes that hold markup: `Text Editor`, `HTML Editor`, `HTML`, `Markdown Editor`,
  `Code`, and `Small Text` rendered without escaping.
- Places a value crosses users: comments, ToDo, workspace link descriptions, list-view
  formatters, tooltips, notification text, dashboard card labels, tags, file names,
  quiz answers, evaluator comments, ticket subjects.
- `rg -n "ignore_xss_filter|no_sanitize|allow_html|\|safe" ` across Python and templates.

## Confirm
- Trace to a concrete sink in JS or a Jinja template that emits the value unescaped.
  A field merely *containing* HTML is not a finding until you find the sink.
- Jinja autoescape is on for `.html` templates; `|safe` and `{% autoescape false %}` turn it
  off. Frappe's `frappe.render_template` on the client does not autoescape.

## Report
Give the payload and the victim's role.
