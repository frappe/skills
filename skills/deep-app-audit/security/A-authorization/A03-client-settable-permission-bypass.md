---
id: A03
area: authorization
---
# A03 — Client-settable permission-bypass parameters

**Scope:** request-reachable arguments that turn permission enforcement off.

**Why:** a parameter named `ignore_*` that reaches the ORM from an HTTP request is almost always
a critical.

## Find
- `rg -n "ignore_permissions|ignore_account_permission|ignore_links|ignore_validate|ignore_mandatory|ignore_share|ignore_user_permissions" --type py`
- For each hit, walk backwards: is the value a literal, or does it come from a function
  parameter that a whitelisted caller can set?
- Also flag `**kwargs` forwarded into `get_doc`, `get_list`, `save`, or `db.get_value`.
- Watch for `doctype` and `parent` parameters passed through from the request — those select
  which permission is checked at all.

## Confirm
- Trace every caller. A parameter is only a finding if some reachable entry point lets the
  client control it.
- `frappe.form_dict` merging means a URL query param can populate a function argument even
  when the caller looks internal.

## Report
Show the HTTP request body that flips the flag.
