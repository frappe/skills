# A02 — IDOR / BOLA: object identity from the request

**Scope:** whitelisted methods that take an object identifier and act on it without proving
the caller owns or may reach that object.

**Why:** the object ID arrives as a request parameter and the handler fetches the record without
asking whether the caller owns it.

## Find
- Parameters named `name`, `docname`, `doc`, `user`, `employee`, `party`, `customer`,
  `supplier`, `team`, `ticket`, `lead`, `student`, `id`, `reference_name`.
- `rg -n "def .*\((.*\b(name|docname|user|employee|party)\b.*)\)" --type py -A 15` then
  check what the function does with it.
- Any function that defaults an owner-ish parameter to `frappe.session.user` but still
  accepts an override.

## Confirm
- An override that a low-privilege actor can set is the bug, even if the default is safe.
- Filtering by `owner` inside a query is a valid check; filtering client-side is not.
- Check the child-table case: reaching a parent through a child row name.

## Report
State the exact request that reaches another user's object.
