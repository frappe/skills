---
id: A24
area: customization
mechanism: M01
semgrep: {rules: [frappe-breaks-multitenancy], coverage: partial}
---
# A24 — A `hooks.py` value is static data, computed once per process

**Why:** `hooks.py` is imported at boot, before a site is chosen, and the merged result is cached
under `app_hooks`. A value computed at import time is computed with the wrong site, or with no
site at all. The result is then served to every site on the bench until the cache is cleared.

## Bad

```python
# my_app/hooks.py
import frappe

app_name = "my_app"

if "hrms" in frappe.get_installed_apps():
	doc_events = {"Employee": {"validate": "my_app.hr.validate_employee"}}

scheduler_events = {
	"cron": {frappe.db.get_single_value("MyApp Settings", "sync_cron"): ["my_app.tasks.sync"]}
}
```

## Good

```python
# my_app/hooks.py
app_name = "my_app"

doc_events = {"Employee": {"validate": "my_app.hr.validate_employee"}}

scheduler_events = {"hourly": ["my_app.tasks.sync"]}
```

```python
# my_app/hr.py
import frappe


def validate_employee(doc, method=None):
	if "hrms" not in frappe.get_installed_apps():
		return
	...
```

## Find

- `rg -n '^(import|from)' hooks.py` beyond `frappe` typing imports.
- `rg -n 'frappe\.(db|get_all|get_doc|get_meta|get_hooks|get_installed_apps|conf|local|flags)' hooks.py`.
- `rg -n '^\s*(if|for|while)\b' hooks.py`.
- A hook value that is the result of a call rather than a literal.
- Semgrep `frappe-breaks-multitenancy` finds module-level assignments from `frappe.db` and
  friends.

## Confirm

`_load_app_hooks` keeps every public module member that is not a module, a function, or a class
(`frappe/__init__.py:_load_app_hooks`). A function assigned to a hook name is dropped silently. A
computed literal is kept, with whatever value it had at import.

Outside developer mode the merged dict is stored in the client cache, so a `hooks.py` change
needs `bench clear-cache` or a migrate before it takes effect. State this when the finding is a
hook change that "did not work".

A conditional that reads only the file system or a constant is a weak finding. A conditional that
reads the database or `frappe.local` is always a finding.

The correct place for a per-site condition is the handler body, or a `before_enable` and
`before_disable` pair that marks the app's customizations.
