---
id: B01
area: injection
---
# B01 — SQL injection: string-built queries, unparameterisable components, second order

**Scope:** every path where a request value or a stored value reaches SQL text. Three cases in
one scope: queries built by string operations, the query components that cannot be
parameterised, and stored values interpolated into a query later.

**Why:** string-built SQL is the classic path from any authenticated user to arbitrary reads.
`order_by` and `group_by` reach SQL unparameterised, so they stay injectable after every other
parameter is fixed. Stored values reach SQL far from the code that accepted them, so the write
looks harmless and the read is the sink.

The three cases share one enumeration, and the second-order case needs the sinks the other two
find. Auditing them together avoids doing the same sweep three times.

## Find — string-built queries
- `rg -n "db\.sql\(|db\.sql_list\(|db\.multisql\(" --type py -A 6`
- Flag any query built with an f-string, `%` formatting, `.format()`, `+` concatenation, or
  `.join()` on a non-literal.
- Report files (`*/report/*/**.py`) and dashboard/chart sources are the densest cluster —
  filters land straight in `WHERE` there.
- `conditions` / `where_clause` helper functions that return SQL fragments.

## Find — unparameterisable components
- `order_by=`, `group_by=`, `fields=`, `having=`, `search_field`, `searchfield`,
  `query`/`reference_doctype` in link-search paths.
- `frappe.desk.reportview.get`, `frappe.desk.search.search_link`,
  `sanitize_searchfield`, `DatabaseQuery.sanitize_fields` and every place they are bypassed.
- Aggregate functions in `fields`: `count(*)`, `sum(...)`, subqueries in a field list.

## Find — second order
- For every interpolated value above that is *not* a request parameter, ask where it was
  stored: a doctype field, a Singles setting, a naming series, a custom field label, a
  translation.
- Fields any low-privilege user can write. These are different in each app: find the doctypes
  where a portal or low-privilege role has `write` at permlevel 0. `Address`, tags, and comment
  text are examples in the framework.
- Naming series and autoname strings — they are concatenated into SQL and Jinja both.

## Confirm
- `%s` with a params tuple is safe. An f-string that interpolates a value into the query text
  is not, even if the value "comes from a filter dict".
- Identifiers (table, column, direction) cannot be parameterised — those need an allowlist,
  not escaping. Absence of an allowlist is the finding.
- `frappe.db.escape` is a partial mitigation; check it is applied to every interpolated value
  and that the result is not wrapped in extra quotes.
- `@validate_and_sanitize_search_inputs` sanitizes `searchfield` and nothing else. It does not
  touch `filters`, and it authorizes nothing. The decorator is not a guard, and its absence is not
  a finding (`_framework-guards.md` section 5).
- A port to the query builder is not a fix by itself. It adds no permission, and it stops an
  identifier injection only when the installed `pypika` escapes identifiers
  (`_framework-guards.md` section 9).
- Unparameterisable sinks support blind and time-based extraction (`sleep()`, `benchmark()`,
  conditional `CASE`), so "you can only control ordering" is still critical.
- Denylist-based sanitisers are the recurring failure — look for a way to express the payload
  without the denied token (comments, alternate syntax, nested functions, unicode).
- A field-list injection also defeats `permlevel` filtering — note that impact.
- A second-order finding needs a reachable write path plus a reachable read path. Show both.
  Length-limited fields still fit useful payloads; do not dismiss on length alone.

## Report
Give the injecting payload, not just the line. For an unparameterisable sink, give a working
blind-extraction payload sketch. For a second-order case, give the two-step chain: the write
request, then the read that fires it.
