---
id: C02
area: xss-client
---
# C02 — Unsafe HTML sinks and Desk DOM XSS

**Scope:** every frontend sink that injects markup — JS, Vue, and frappe-ui code, plus the Desk
form, list, report, and workspace renderers.

**Why:** `v-html`, `innerHTML`, and equivalent sinks bypass framework escaping, including inside
shared UI components. The Desk renderers are the same class of sink with a higher-privilege
victim — they render arbitrary document data for System Managers, so a hit there is a path to
Administrator.

**Applies to:** the framework repository for the core Desk renderers. For an app checkout, audit
only what the app adds: custom formatters, custom controls, DocType client scripts, report
`formatter` functions, and any Desk page the app ships.

## Find — generic sinks
- `rg -n "innerHTML|outerHTML|v-html|dangerouslySetInnerHTML|insertAdjacentHTML|document\.write" -g '*.js' -g '*.vue' -g '*.ts'`
- jQuery: `.html(`, `.append(`, `.prepend(`, `.after(`, `.before(`, `$(<var>)` where the
  variable is data.
- `frappe.render_template` and `__()` results passed into any of the above.
- Vue templates rendering error messages, markdown output, or API responses.

## Find — Desk renderers
- Field formatters (in the framework, `<app>/public/js/frappe/form/formatters.js`) and control
  classes — which build HTML from values.
- List view: `get_indicator`, subject/comment/like renderers, group-by counts, link titles.
- Report view and Query Report: cell formatters, custom `formatter` functions in report JS.
- Workspace: shortcut and card link labels, number card values.
- Grid rows, `HTML` fieldtype rendering, `Attach` field filename display.
- Awesome Bar, global search result rendering, keyboard-shortcut hints.

## Confirm
- Follow the value back to an API response or a document field. A constant string is not a
  finding.
- Note whether a sanitizer is applied and whether it runs before or after interpolation.
- The attacker input is usually a document field or a file name written by a lower role.
  Identify that role.

## Report
`file:line` of the sink plus the source of the data. High severity when the victim is a
System Manager.
