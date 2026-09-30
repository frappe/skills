# B07 — `safe_exec` / `safe_eval` / Server Script sandbox

**Scope:** the Python sandbox used by Server Script, Client-callable scripts, and dynamic
evaluation helpers.

**Applies to:** the framework repository for the sandbox itself. For an app checkout, audit
the app's own `safe_eval` callers and any name the app adds to the sandbox globals.

**Why:** the sandbox runs user-written code in the server process, so every addition to its
globals widens what that code can reach.

## Find
- `rg -n "safe_exec|safe_eval|NamespaceDict|get_safe_globals|_getattr|_write_" --type py`
- Enumerate every name in the safe globals and every whitelisted attribute. For each, ask
  what it can reach transitively.
- Callers of `safe_eval` on non-constant input outside Server Script: condition fields in
  Notification, Workflow, Assignment Rule, Auto Repeat, Dashboard Chart filters, Web Form
  `depends_on`, `mandatory_depends_on`, `read_only_depends_on`.
- Who can create or edit a Server Script, and is `server_script_enabled` the only gate?
- `frappe.safe_eval` used to evaluate a *filter* string from the request.

## Confirm
- The bar is: from inside the sandbox, reach arbitrary attribute access, arbitrary import,
  file IO, or `frappe.db.sql` with attacker-controlled text.
- Note that `safe_eval` restrictions and `safe_exec` restrictions differ — test both.

## Report
Critical by default. Include the exact sandbox payload.
