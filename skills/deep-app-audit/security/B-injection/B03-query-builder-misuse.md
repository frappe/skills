---
id: B03
area: injection
---
# B03 — Query Builder misuse

**Scope:** `frappe.qb` usage where structure comes from the request.

**Why:** query builder wrappers read as safe but pass raw fragments through in several places,
and their permission switch is off by default.

## Find
- `rg -n "frappe\.qb\.DocType\(|qb\.Table\(|qb\.get_query\(" --type py` — flag any
  argument that is a variable traceable to a request.
- `qb.get_query(...)` in app code: does the wrapper preserve
  permission handling, or does the override drop it?
- Filter keys that reach `table[field]`. A key becomes a column name, and a loop over
  `filters.items()` lets the caller choose it.
- `.views.query_builder_unpermissioned` in the inventory: each query builder read that does not
  pass `ignore_permissions=False`.
- `Criterion`, `CustomFunction`, `LiteralValue`, `Field(...)` built from user strings —
  `LiteralValue` is a raw-SQL escape hatch.
- `.run(as_dict=True)` on a query whose `select` list came from the client.

## Confirm
- **The permission switch is off by default.** `frappe.qb.get_query` takes
  `ignore_permissions=True` by default, and a query built from `frappe.qb.DocType(...)` applies
  no permission at all. Quote the argument at the call site. Do not infer it.
- When `get_query` applies permissions, it checks `select`, not `read`. A role gap computed on
  `read` tests a right that this path does not check (`_framework-guards.md` section 3).
- QB escapes *values*. Whether it escapes an identifier depends on the installed `pypika`, not
  on the pin (`_framework-guards.md` section 9). Read `pypika.utils.format_quotes` in the
  environment of the bench, and say which implementation you saw. `LiteralValue` and
  `CustomFunction` bypass escaping in all versions.
- An identifier from an allowlist, from `meta.get_valid_columns()`, or from a literal is safe.
- An app-level `get_query` override that changes the permission semantics is an
  authorization finding as much as an injection one — cross-file to `A06`.

## Report
Name the QB construct that carries the payload, quote the `ignore_permissions` argument at the
call site, and state which `format_quotes` implementation the bench has.
