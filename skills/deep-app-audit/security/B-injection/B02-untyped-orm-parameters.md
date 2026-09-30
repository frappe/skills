---
id: B02
area: injection
---
# B02 — Injection via untyped parameters into the ORM

**Scope:** whitelisted methods that pass a request value straight into `get_all`, `get_list`,
`get_value`, `exists`, `count`, or `delete` where a scalar was assumed.

**Why:** the canonical case is a `secret_key` parameter answered with
`{"secret_key": ["!=", ""]}`. An untyped value that reaches the ORM becomes a filter operator.

## Find
- Whitelisted functions with no type annotations on their parameters.
- `rg -n "db\.exists\(|db\.get_value\(|db\.count\(|get_all\(|get_list\(" --type py`
  and check whether any argument is an un-coerced request parameter.
- `filters=` built from `frappe.form_dict`, `json.loads(frappe.form_dict...)`, or a `filters`
  parameter forwarded verbatim.
- `or_filters`, `having`, `pluck`, `distinct` taken from the request.

## Confirm
- Frappe deserialises JSON request bodies, so a parameter declared as a string can arrive as
  a list or dict. Absence of `str()`/`cstr()`/type annotation is what makes it exploitable.
- A `frappe.db.exists("DocType", user_value)` where `user_value` can be a dict is an
  authentication bypass, not just an injection.

## Report
Show the JSON body that changes the query's meaning.
