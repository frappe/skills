# Fix SQL injection in a Frappe app

**SQL has two kinds of position, and they are fixed differently.** A **value** (`= x`, `LIKE x`,
a date) is bound as a parameter. An **identifier** (column, table/DocType, `ORDER BY` key, a
`SELECT` item, a filter *key*) can never be bound by any driver — it is checked against an
**allow-list**. Nearly every real case is an identifier treated like a value, next to values that
were already parameterised correctly.

## Steps

### 1. Map every interpolation in the query

For the vulnerable function — and every query in the same function and its helpers — list each
non-constant piece and classify it: **value**, **identifier**, or **fragment** (a whole SQL
clause). Note where each one comes from: the request, a stored record (docnames, settings rows), or
code.

Done when: every `{}`, `%s`, `+`, `.format`, f-string and `t[...]` in the query is on the list with
its source. A piece from code (`date_field` chosen by an `if`) is safe. The same piece from
`filters` is not, and that distinction is the whole review question.

### 2. Fix each position

| Position | Fix |
|---|---|
| **Value** | named parameters — `frappe.db.sql("… where x = %(x)s", {"x": v})` — or a `frappe.qb` comparison (`t.field == v`, `t.field.like(f"%{v}%")`), which emits a bound parameter |
| **Value, where the query must stay a string** | `frappe.db.escape(v)` **without** surrounding quotes — it returns the value already quoted. Use `percent=False` when the string is not `%`-formatted afterwards |
| **Identifier from a known set** | a literal `set` or `dict` map. `frappe.throw` on a miss |
| **Identifier naming a field** | `if field not in frappe.get_meta(dt).get_valid_columns(): frappe.throw(...)`, or `meta.has_field(field)` |
| **DocType / table name** | a closed allow-list first, then `frappe.qb.DocType(name)`. Its own name check stops a backtick breakout but deliberately allows `__Auth`, so it does not stop table *choice* |
| **Numeric `LIMIT` / `OFFSET`** | `cint(v)` |
| **A SQL fragment parameter** | delete it. Take structured filters and build the clause server-side. There is no safe way to accept SQL from a caller |
| **A stored identifier** (a settings row whose `fieldname` later becomes a column) | validate it in the settings doctype's `validate()` against meta, *and* allow-list again at the reader |
| **A stored docname** | bind it like any value — request-time sanitisation never sees a value stored earlier |

When `fields` or `filters` come from the caller, `frappe.get_query(t, fields=…, filters=…)` on
`develop` validates both through frappe's query engine. **Older majors validate less** — on
version-15 filter keys are only checked with `validate_filters=True` and `fields` validation is
much weaker — so when the fix must also land there, allow-list against `get_valid_columns()`
yourself.

A validator must **raise** on a miss, and must run for every row: one that only `frappe.log_error`s
and drops the row, or that returns "valid" on a caller-supplied discriminator
(`if row.data_source != "x": return valid`), leaves the hole open.

Done when: every entry from step 1 is bound, allow-listed, from code, or deleted.

### 3. Fix the other half

**Removing the injection does not add authorization.** `frappe.qb.from_()` applies no permissions,
and `frappe.get_query` defaults to `ignore_permissions=True`. A whitelisted endpoint ported from
string SQL to `qb` still reads any row it is handed. Check the endpoint against
[classes/missing-authorization.md](missing-authorization.md) in the same change.

Done when: the endpoint either applies permissions (`get_query(..., ignore_permissions=False)`,
`get_list`, or `frappe.has_permission(..., doc=)`) or you have recorded why it does not need them.

### 4. Verify

Run as a low-privilege user, against the pre-fix code and then the fix, on every release line:

| Position | Payload | Before | After |
|---|---|---|---|
| `fields` item | ``name` FROM `tabUser` -- `` | rows from `tabUser` | validation error |
| `filters` key (JSON body) | `` {"idx`=`idx` AND (SELECT COUNT(*) FROM `tabUser` WHERE name='Administrator')>0 -- ": "1"} `` and the same with a false predicate | rows vs `[]` | rejected both ways |
| value | `' OR SLEEP(5) -- ` | delay | literal match, no delay |
| DocType filter | any name outside the allow-list | SQL error or foreign rows | "Invalid value" |
| stored | save the payload as a docname or settings fieldname, then trigger the reader | leak on trigger | rejected at save, or bound at read |

- **Known-positive control first** ([verify.md](../verify.md)):
  the payload must fire on the pre-fix code.
- **Boolean pairs, not single requests:** true and false predicates must differ before, match after.
- **Error codes discriminate** (MariaDB): `1054 Unknown column` is a bogus column, `1064` is a
  breakout. After the fix both become a framework validation error before SQL runs.
- **Pass a real DocType** to search endpoints: `@frappe.validate_and_sanitize_search_inputs` returns
  `[]` without calling the function for a non-existent one — a fabricated "safe". That decorator
  only sanitises `searchfield`, `start` and `page_len`. It never inspects `filters` or `txt`.
- **Run the legitimate call too:** valid `fields`/`filters` must still return the expected rows —
  allow-lists break callers that passed `"tab.field as alias"`.
- **Record the installed pypika.** Whether `t[user_input]` escapes an embedded backtick depends on
  the `format_quotes` in the bench's environment, not the pinned version:
  `env/bin/python -c "import pypika.utils,inspect;print(inspect.getsource(pypika.utils.format_quotes))"`.
  A fix must not depend on it — allow-list identifiers regardless.

Done when, on every release line: every payload fired before and is rejected after, the legitimate call returns the same
rows as before, and the result names the pypika implementation it ran on.

## Pitfalls

- **A query-builder port is not automatically an injection fix.** It parameterises values and does
  nothing for `qb.DocType(filters["x"])`, `t[filters["y"]]` or `.orderby(t[key])`.
- `'{frappe.db.escape(x)}'` double-quotes. `.replace("'", "'")` is a no-op that looks like escaping.
- Frappe's blacklist helpers (`sanitize_column`, `sanitize_searchfield`, `sanitize_fields`) have
  each been tightened over time. They are frappe's defence in depth. In app code an allow-list of
  real column names is the fix.
- A fix at the writer (settings `validate()`) leaves the reader unchanged — read both ends before
  calling it unfixed.

## References

- Shipping, backports and the public PR: [the security workflow](../workflow.md).
