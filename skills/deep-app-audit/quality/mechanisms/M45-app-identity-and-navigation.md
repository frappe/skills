---
id: M45
---
# M45 — App identity and navigation

**What:** `add_to_apps_screen` puts the app on the apps screen with a name, a title, a route, a
logo, a sort key and an optional `has_permission` path. `app_title`, `app_logo_url` and
`app_home` are the older, single-value forms of the same three values. `standard_navbar_items`
and `standard_help_items` seed the two navbar dropdowns. `code_only_modules` maps a module that
ships no navigation to the modules that carry its navigation now. `domains` maps a domain name
to the module that holds its data.

**Guards:** Boot reads these hooks one app at a time and takes the first entry, so an app
declares its own identity and cannot change another app's. `has_permission` is a dotted path to
a function of no arguments; when it returns a false value the app keeps its name but loses its
route and its dock. `add_standard_navbar_items` seeds Navbar Settings only when both dropdowns
are empty, so the hook is read once on a fresh site and never again. An app that pins into
another app's rail takes no slot of its own on the apps screen.

## Good use

The app declares one entry with everything the apps screen needs.

```python
# hooks.py
add_to_apps_screen = [
	{
		"name": "my_app",
		"logo": "/assets/my_app/images/logo.svg",
		"title": "My App",
		"route": "/my-app",
		"has_permission": "my_app.utils.has_app_permission",
	}
]
```

```python
# my_app/utils.py
import frappe


def has_app_permission():
	return bool(frappe.get_roles() and "My App User" in frappe.get_roles())
```

The permission function is cheap. It runs on every desk boot for every user.

Every dotted path in these hooks is read at boot, so a path that no longer resolves breaks the
apps screen rather than one feature.

Navbar items are a first-install convenience. An app that needs a navbar entry on a site that
already has one adds the row itself, in an install hook, and removes it on uninstall. It does
not rely on the seed hook running again.

The values in `hooks.py` are static data. A title or a logo computed at import time is computed
before a site is chosen and is then cached for every site on the bench.

## Rules

- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve.
- A24 — A `hooks.py` value is static data, computed once per process.
- A10 — Remove the app's Custom Fields and Property Setters on uninstall.
