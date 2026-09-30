---
id: A11
area: customization
mechanism: M02
---
# A11 — Declare hard dependencies in `required_apps`. Guard optional ones

**Why:** An app with an undeclared hard dependency installs on a bare site and fails at the
first import. An app that lists an optional product as required cannot be installed by anyone
who does not want that product.

## Bad

```python
# my_app/hooks.py
required_apps = ["erpnext", "hrms"]
after_install = "my_app.setup.install.after_install"
```

```python
# my_app/setup/install.py
def after_install():
	create_custom_fields(SALES_FIELDS)
	create_custom_fields(PAYROLL_FIELDS)  # HRMS DocTypes
```

## Good

```python
# my_app/hooks.py
required_apps = ["erpnext"]
after_install = "my_app.setup.install.after_install"
after_app_install = "my_app.setup.install.after_app_install"
```

```python
# my_app/setup/install.py
import frappe


def after_install():
	create_custom_fields(SALES_FIELDS)
	if "hrms" in frappe.get_installed_apps():
		create_custom_fields(PAYROLL_FIELDS)


def after_app_install(app_name):
	"""Add the payroll fields when HRMS arrives after this app."""
	if app_name == "hrms":
		create_custom_fields(PAYROLL_FIELDS)
```

## Find

- `rg -n 'required_apps' hooks.py`.
- `rg -n '^\s*(import|from)\s+(erpnext|hrms|frappe\.\w+)' --type py` and compare the app names
  with `required_apps`.
- `rg -n 'after_app_install|after_app_uninstall' hooks.py` in an app that customizes an optional
  app.
- In install code, `create_custom_fields` or `frappe.get_meta` on a DocType from an app that is
  not required and has no `in frappe.get_installed_apps()` guard.

## Confirm

`install_app` installs `required_apps` first and then runs `before_install`
(`frappe/installer.py:install_app`). `after_app_install` runs for every installed app whenever
any app is installed, which is the hook that covers a later install of an optional app.

An import of an optional app inside a function body, reached only under a guard, is not a
finding. An import at module level is, because the module loads at boot.

`frappe.get_attr` throws `AppNotInstalledError` when the first path segment is not an installed
app (`frappe/utils/__init__.py:get_attr`). A hook path that names an optional app breaks boot
on a site without it.
