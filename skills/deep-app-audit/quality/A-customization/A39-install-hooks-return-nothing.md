---
id: A39
area: customization
mechanism: M02
---
# A39 — A `before_install` hook must not return a value

**Why:** `install_app` stops the whole install when a `before_install` hook returns `False`. A
helper that ends with a call to a function returning a falsy value aborts the install silently.
The app appears in `apps.txt`, nothing is synced, and the site is half-installed.

## Bad

```python
# my_app/setup/install.py
import frappe


def before_install():
	return frappe.db.exists("Company", {"country": "Atlantis"})
```

On a site with no Atlantis company this returns `None`, and the install stops.

## Good

```python
# my_app/setup/install.py
import frappe
from frappe import _


def before_install():
	if not frappe.db.exists("DocType", "Company"):
		frappe.throw(_("MyApp needs ERPNext. Install ERPNext first."))
```

## Find

- `rg -n 'before_install' hooks.py`, then read the hook body.
- Any `return` statement in the hook or in the last call it makes.
- A hook whose last line is an expression call rather than a statement.

## Confirm

`install_app` runs each `before_install` hook and returns from the whole install when the result
is `False` (`frappe/installer.py:install_app`). Only the literal `False` stops it, so `None` from
a bare function is safe and a falsy database result is not.

An intentional `return False` is valid when the app must refuse the install. State the reason to
the user first, because the install stops with no message.

The same reading applies to `before_uninstall`, which has no such guard, and to `after_install`,
whose return value is ignored.

`before_install` runs before `sync_for`, so the app's own DocTypes do not exist yet. A hook that
reads them is a separate finding.
