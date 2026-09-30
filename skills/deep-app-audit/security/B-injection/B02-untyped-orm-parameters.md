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
- Parameters that can carry a list or a dict. From Frappe 15, `@frappe.whitelist()` validates
  annotations with pydantic, so `name: str` rejects a list with 417. The parameters that can
  carry a container are: annotated `dict` or `list`, with no annotation, with a string
  annotation, or in a module with `from __future__ import annotations` (each annotation is then
  a string, and pydantic skips it). A default of another type also widens the type: `name: str =
  {}` accepts a dict. Read the signature and the top of the module first
  (`_framework-guards.md` section 4).
- `.entry_points[].container_params` in the inventory lists these parameters, and
  `.views.container_param_reaching_auth_sink` narrows to those near a document or permission sink.
- Values inside a `dict` parameter. `filters: dict` validates the container only.
- `rg -n "db\.exists\(|db\.get_value\(|db\.count\(|get_all\(|get_list\(" --type py`
  and check whether any argument is an un-coerced request parameter.
- `filters=` built from `frappe.form_dict`, `json.loads(frappe.form_dict...)`, or a `filters`
  parameter forwarded verbatim.
- `or_filters`, `having`, `pluck`, `distinct` taken from the request.

## Confirm
- Frappe deserialises JSON request bodies, so a parameter that is not validated can arrive as a
  list or dict. Absence of a validated scalar annotation, `str()`, or `cstr()` is what makes it
  exploitable. A validated scalar annotation refutes the candidate.
- A permission check can be correct and still not enough. When the endpoint takes a name out of
  a `dict`, authorizes the document of that name, then queries with the same dict, an operator
  widens the query after the check (`_framework-guards.md` section 4a).
- A 500 is not a control. A list payload that fails with an `AttributeError` in `has_permission`
  stopped by accident.
- The function must use the parameter. A search helper that accepts `filters` and ignores it is
  a false positive.
- The request shape is part of the finding. A `dict` parameter is a dict only in a JSON body. A
  form-encoded value gets 417.
- A `frappe.db.exists("DocType", user_value)` where `user_value` can be a dict is an
  authentication bypass, not just an injection.

## Report
Show the JSON body that changes the query's meaning, the annotation (or its absence) that let
it through, and what came back that must not.
