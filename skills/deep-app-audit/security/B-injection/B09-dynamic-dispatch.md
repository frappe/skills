# B09 — Dynamic dispatch: arbitrary callable from the request

**Scope:** request-controlled function or module resolution.

**Why:** dynamic dispatch resolves a request-controlled string to a callable. A retry or replay
handler that reads a stored method path is the common case.

## Find
- `rg -n "frappe\.get_attr|get_attr\(|getattr\(|importlib|__import__|frappe\.call\(|eval\(|exec\(|compile\(" --type py`
- Fields storing a dotted path that is later resolved: `method`, `handler`, `callback`,
  `queue_method`, `reference_method`, retry/replay handlers, integration request methods,
  webhook handlers, `Scheduled Job Type.method`, `Server Script.script_type`.
- `frappe.enqueue(method=<from request>)` and `enqueue_doc` with a client-supplied method
  name — cross-reference `K02`.
- Who can write the doctype that stores the dotted path.

## Confirm
- An allowlist of permitted paths, or a `@frappe.whitelist`-only resolution, is the mitigation.
  Check the allowlist actually constrains — a prefix match on the app name is not enough.

## Report
Name the field, who writes it, and what executes it.
