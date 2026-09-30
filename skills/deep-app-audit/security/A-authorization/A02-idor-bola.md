---
id: A02
area: authorization
---
# A02 — IDOR / BOLA: object identity from the request

**Scope:** whitelisted methods that take an object identifier and act on it without proving
the caller owns or may reach that object.

**Why:** the object ID arrives as a request parameter and the handler fetches the record without
asking whether the caller owns it.

## Find
- Parameters named `name`, `docname`, `doc`, `user`, `id`, `reference_name`, and the names of
  the entities of the app. Read its DocType list, do not guess business nouns.
- `rg -n "def .*\((.*\b(name|docname|user|employee|party)\b.*)\)" --type py -A 15` then
  check what the function does with it.
- Any function that defaults an owner-ish parameter to `frappe.session.user` but still
  accepts an override.
- An identifier that arrives inside a `dict` parameter. It can carry an operator as well as a
  name (`_framework-guards.md` section 4a). `.views.container_param_reaching_auth_sink` lists
  these.

## Confirm
- An override that a low-privilege actor can set is the bug, even if the default is safe.
- Filtering by `owner` inside a query is a valid check; filtering client-side is not.
- Check the child-table case: reaching a parent through a child row name.
- A load through `frappe.get_doc(dt, name).save()` or `.delete()` is checked by the document
  layer. A plain `frappe.get_doc(dt, name)` whose values are returned is not.
- The object must belong to someone else. When the target doctype grants `read` at permlevel 0
  to an automatic role or to a role of the actor, the actor can read it, and there is no finding.
- With a site, compare with `/api/resource/<DocType>/<name>` in the same session. A 200 there
  refutes the finding. An empty 200 from the endpoint is an acquittal.

## Report
State the exact request that reaches another user's object, the value that it returned, and
what the same session got from `/api/resource/<DocType>/<name>`.
