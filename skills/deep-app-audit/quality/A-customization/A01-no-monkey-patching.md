---
id: A01
area: customization
mechanism: M58
semgrep: {rules: [frappe-monkey-patching-not-allowed], coverage: partial}
---
# A01 — Do not replace a framework or app function at import time

**Why:** A patched function freezes core logic at one version. Later core fixes never reach the
patched code. The patch also applies to every site on the bench, not only to the sites that
installed the app, because it runs once per Python process.

## Bad

```python
# my_app/__init__.py
import frappe.utils.data

_original = frappe.utils.data.fmt_money


def fmt_money(amount, precision=None, currency=None, format=None):
	return _original(amount, precision, currency, format).replace(",", " ")


frappe.utils.data.fmt_money = fmt_money
```

## Good

```python
# my_app/hooks.py
jinja = {"methods": ["my_app.utils.fmt_money_spaced"]}
```

```python
# my_app/utils.py
from frappe.utils import fmt_money


def fmt_money_spaced(amount, currency=None):
	"""Format money with a space as the group separator, for print formats only."""
	return fmt_money(amount, currency=currency).replace(",", " ")
```

## Find

- `rg -n '^\s*(frappe|erpnext|hrms)[\w.]*\.\w+\s*=' --type py` in the app.
- `rg -n 'setattr\(\s*(frappe|erpnext)' --type py`.
- Every module that runs at import: `__init__.py`, `hooks.py`, and any module a hook path imports.
- Semgrep `frappe-monkey-patching-not-allowed` finds the `import x` then `x.a.b = ...` shape.

## Confirm

An assignment to an attribute of the app's own module is not a finding. A finding needs the
target to belong to `frappe`, to a first-party app, or to a third-party package.

An assignment inside a test file or inside a `unittest.mock.patch` block is not a finding.

A patch in `hooks.py` never reaches the framework as a hook: `_load_app_hooks` drops functions
and classes (`frappe/__init__.py:_load_app_hooks`). The patch still runs, because importing
`hooks.py` runs the module. Treat it as a finding.

Ask which documented mechanism does the same work. A hook, `extend_doctype_class` (A03), a
`jinja` method (A32), or a `regional_overrides` entry (A04) covers almost every case.
