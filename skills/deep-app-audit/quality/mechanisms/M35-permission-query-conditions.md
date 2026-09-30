---
id: M35
---
# M35 — `permission_query_conditions`

**What:** The `permission_query_conditions` hook adds a `WHERE` condition to every list query for
one doctype, or for every doctype under the `*` key. It is what removes rows from a list view, a
report view, a link search and `frappe.get_all`.

**Guards:** The methods for the doctype run first, then the methods under `*`, in list order, and
every non-empty result is joined with `and`. A handler receives the user as a positional argument
and the doctype as a keyword argument, and the call goes through `frappe.call`. A handler returns
a SQL string or a pypika term; a term is rendered to SQL with the dialect's quote character and
its values are inlined with the driver's escaping. After the hooks, the Permission Query Server
Script for the doctype, if there is one, appends its own condition.

The condition is added to a query that already has its tables. A condition that names a table the
query does not join fails the query for every caller, including the desk list view. Child tables
that the query did join are passed to a Server Script as `active_child_tables`, and to a hook they
are not passed at all.

This hook shapes results. It is not a permission check: `frappe.get_doc` and a direct read do not
run it.

## Good use

Write the condition against the main table, named `tab<DocType>`, and keep it to columns of that
table.

```python
def delivery_trip_query(user, doctype=None):
    branches = get_allowed_branches(user)
    if not branches:
        return ""
    return f"`tabDelivery Trip`.branch in ({', '.join(frappe.db.escape(b) for b in branches)})"
```

Return an empty string when the rule does not apply to the user, so the query is left alone.
Returning a condition that is always false is the way to show nothing, and it must be a
deliberate choice.

Filter on an indexed column. The condition is added to every list query on the doctype, so an
unindexed column turns every list page into a full table scan.

Use a pypika term when the condition holds values, so the framework escapes them. A string that
interpolates a value has to escape it with `frappe.db.escape`.

Keep the condition portable, or branch on `frappe.db.db_type`. The same string runs on MariaDB,
on Postgres and on SQLite.

## Rules

- A25 — A hook handler accepts every argument the call site passes
- A28 — A permission hook can only narrow a result, and only where the framework reads it
- B38 — Keep SQL portable, or branch on the database type
