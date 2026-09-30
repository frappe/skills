---
id: B03
area: injection
---
# B03 — Query Builder misuse

**Scope:** `frappe.qb` usage where structure comes from the request.

**Why:** query builder wrappers read as safe but pass raw fragments through in several places.

## Find
- `rg -n "frappe\.qb\.DocType\(|qb\.Table\(|qb\.get_query\(" --type py` — flag any
  argument that is a variable traceable to a request.
- `qb.get_query(...)` in app code: does the wrapper preserve
  permission handling, or does the override drop it?
- `Criterion`, `CustomFunction`, `LiteralValue`, `Field(...)` built from user strings —
  `LiteralValue` is a raw-SQL escape hatch.
- `.run(as_dict=True)` on a query whose `select` list came from the client.

## Confirm
- QB escapes *values*. It does not validate identifiers, and `LiteralValue`/`CustomFunction`
  bypass escaping entirely.
- An app-level `get_query` override that changes the permission semantics is an
  authorization finding as much as an injection one — cross-file to `A06`.

## Report
Name the QB construct that carries the payload.
