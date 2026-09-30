# B04 — Multi-statement execution and SQL file primitives

**Scope:** whether a single injection point can execute more than a `SELECT`.

**Why:** multi-statement execution and SQL file primitives are the difference between a data
leak and RCE.

## Find
- DB driver configuration: `mysqlclient` connection flags allowing multiple statements;
  PostgreSQL paths where `;`-separated statements execute.
- `local_infile` setting on the MariaDB connection.
- `check_safe_sql_query` and every caller — look for bypasses: `SELECT ... INTO OUTFILE`,
  `INTO DUMPFILE`, `LOAD_FILE`, CTEs, `HANDLER`, stacked comments, leading whitespace or
  parentheses that defeat a prefix check.
- System Console / Server Script SQL execution: is it really read-only?
- `frappe.db.sql` calls with `run=False` whose string is later executed elsewhere.

## Confirm
- Prove the bypass against the actual sanitiser code in this checkout, not from memory.

## Report
Mark anything reaching a file-write primitive as Critical.
