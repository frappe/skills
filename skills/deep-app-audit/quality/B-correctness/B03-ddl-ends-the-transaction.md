---
id: B03
area: correctness
---
# B03 — Keep schema statements out of a transaction that holds writes

**Why:** `CREATE`, `ALTER`, `DROP` and `TRUNCATE` are DDL. The database commits the open
transaction before it runs them, and the statement cannot be rolled back. A patch that writes
rows and then runs DDL commits those rows early, so a later failure cannot undo them.

## Bad

```python
# my_app/patches/v1_0/add_route_flag.py
def execute():
    frappe.db.sql("update `tabRoute` set is_active = 1 where is_active is null")
    frappe.db.sql_ddl("alter table `tabRoute` add column `region` varchar(140)")
    set_regions()  # a failure here cannot undo the update above
```

## Good

```python
# my_app/patches/v1_0/add_route_flag.py
def execute():
    frappe.reload_doc("my_app", "doctype", "route")
    frappe.db.sql("update `tabRoute` set is_active = 1 where is_active is null")
    set_regions()
```

## Find

- `rg -n 'sql_ddl|alter table|create table|drop table|create index' -i --type py` in the app.
- `rg -n 'frappe\.db\.truncate\(' --type py`. `truncate` is DDL
  (`source:frappe/database/database.py:Database.truncate`). `frappe.db.delete` is DML and rolls
  back.
- `rg -n 'add_index|alter table' -i --type py` inside a whitelisted method or a lifecycle
  method. A schema change belongs in a patch, in the DocType JSON, or in `on_doctype_update`.

## Confirm

DDL at the start of a patch, before any row write, is correct. `on_doctype_update` on a
controller is the supported place for an index and is not a finding. A schema change that a
DocType JSON change can express does not need raw DDL at all.

On develop the framework detects this case and raises `ImplicitCommitError` when a `create`,
`alter`, `drop`, `truncate`, `start` or `begin` statement runs after a write in the same
transaction (`source:frappe/database/database.py:Database.check_implicit_commit`). The failure
is therefore a hard error on develop and a silent early commit on version 14 and earlier. A
DocType Event Server Script cannot call `add_index` at all, because `safe_exec` removes the name
from the script namespace for that script type (`source:frappe/utils/safe_exec.py:safe_exec`).
