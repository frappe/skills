---
id: A28
area: customization
mechanism: M34
---
# A28 — A permission hook can only narrow a result, and only where the framework reads it

**Why:** A `has_permission` hook that returns `None` denies, because the framework treats every
falsy value as a denial. A `permission_query_conditions` hook is read by `get_list` only. Code
that expects either hook to widen access, or to apply everywhere, ships a rule that does not run.

## Bad

```python
# my_app/projects.py
def permission(doc, ptype=None, user=None, **kwargs):
	if user in get_project_members(doc.name):
		return True
	# Falls through to None for everyone else, which denies every other user.
```

```python
# my_app/reports/utils.py
def get_open_projects():
	# permission_query_conditions is not applied by get_all
	return frappe.get_all("Project", filters={"status": "Open"})
```

## Good

```python
# my_app/projects.py
def permission(doc, ptype=None, user=None, **kwargs):
	"""Deny write on a closed project. Grant nothing."""
	if ptype in ("write", "delete") and doc.status == "Closed":
		return False
	return True
```

```python
# my_app/reports/utils.py
def get_open_projects():
	return frappe.get_list("Project", filters={"status": "Open"})
```

## Find

- `rg -n 'has_permission|permission_query_conditions' hooks.py`, then read each handler.
- A `has_permission` handler with a code path that ends without an explicit `return True`.
- `rg -n 'frappe\.get_all\(' --type py` in code that documents itself as permission-aware.
- A `permission_query_conditions` handler that returns a string naming a table the query does not
  join.

## Confirm

`has_controller_permissions` runs the DocType hooks and then the `*` hooks in reverse order and
returns on the first falsy result (`frappe/permissions.py:has_controller_permissions`). Only a
`True` from every hook allows the action. The public hooks page states that `None` falls back to
default behaviour. That is wrong on develop.

`get_permission_query_conditions` is called from `DatabaseQuery` only when permissions apply
(`frappe/model/db_query.py`). `frappe.db.get_all` sets `ignore_permissions`, so the hook does not
run there, and neither does `frappe.qb.get_query` by default.

A handler that returns a pypika term is valid: the framework renders it to SQL.

A condition that references a table the main query does not include produces invalid SQL for
every list load of that DocType.
