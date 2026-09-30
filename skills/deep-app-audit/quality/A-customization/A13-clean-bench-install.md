---
id: A13
area: customization
---
# A13 — Every module the app imports at load must be declared and present

**Why:** This is the largest cause of full site downtime from a custom app. A module that
imports a package the app never declared works on the developer's bench and fails at boot on
every other bench. The site returns 500 for every request until the app is removed.

## Bad

```python
# my_app/hooks.py
import pandas as pd
from my_app.reports.helpers import load_frame

app_name = "my_app"
app_title = "My App"
```

## Good

```python
# my_app/hooks.py
app_name = "my_app"
app_title = "My App"
```

```python
# my_app/reports/sales_summary.py
def execute(filters=None):
	import pandas as pd  # declared in pyproject.toml, imported where it is used

	return build_columns(), build_rows(pd, filters)
```

## Find

- Collect every top-level `import` and `from ... import` in the app.
- Compare the package names against `pyproject.toml` and `requirements.txt`.
- `rg -n '^(import|from) ' hooks.py __init__.py` and every module named in `patches.txt`.
- `rg -n '__version__' my_app/__init__.py`. A missing version string breaks the bench install.
- `git ls-files | rg 'node_modules/'`. A committed `node_modules` folder breaks the asset build.

## Confirm

The test is an install on a bench that has only frappe, the app's `required_apps`, and the app.
An import error at that point is certain, not a candidate.

An import inside a function body is not a finding for boot. It is still a finding when the
package is undeclared, because the failure moves to the first call instead of to boot.

A standard-library module is never a finding.

`hooks.py` and `__init__.py` are the highest-value files, because the framework imports both on
every request.
