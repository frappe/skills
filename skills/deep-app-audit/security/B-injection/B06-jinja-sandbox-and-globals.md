# B06 — Jinja sandbox escape and dangerous template globals

**Scope:** what is reachable from inside a template once SSTI or a legitimate template exists.

**Applies to:** the framework repository for the sandbox itself. For an app checkout, audit
the app's `jinja` hook entries and any template global the app registers — the sandbox core
is out of scope, but every name the app adds to it is in scope.

**Why:** the Jinja sandbox is only as strong as the globals list exposed to it.

## Find
- The safe-globals definition for templates (in the framework, `<app>/utils/safe_exec.py`;
  jinja environment setup; `hooks.py` `jinja` entries: `methods`, `filters`).
- Every method exposed there: does any of them reach `frappe.db.sql`, file IO, HTTP requests,
  `frappe.get_doc` with `ignore_permissions`, `os`, `subprocess`, or object internals?
- Known escape shapes: `frappe.qb.terms.*` (`Not`, `Criterion`), `format_map`, generator and
  frame internals (`gi_frame`, `cr_frame`), `__class__`/`__mro__`/`__subclasses__` reachable
  through any exposed object, `__globals__` on an exposed function.
- App-level `jinja` hook additions — those are app-specific attack surface.

## Confirm
- Try to reach one dangerous primitive from one exposed name; a chain of two attribute
  accesses is enough to call it a finding.
- Any *addition* to the globals list in the target repo's history is a review trigger even if you
  cannot escape it today.

## Report
Show the attribute chain from an exposed name to the primitive.
