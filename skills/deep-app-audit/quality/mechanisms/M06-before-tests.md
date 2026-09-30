---
id: M06
---
# M06 — `before_tests`

**What:** `before_tests` runs once per app, before the test runner collects that app's tests. It
is the place where an app prepares the state its tests assume: a completed setup wizard, a
company, a fiscal year, a default warehouse.

**Guards:** The hook is read with `frappe.get_hooks("before_tests", app_name=app)`, so only the
app's own value runs for that app. The runner calls it with no arguments. It runs on the test
site with a database connection, so it may write. It runs once, not once per test, so a test
that changes what the hook created leaves the change behind for the tests that follow.

## Good use

Create the smallest set of records that the app's tests cannot create for themselves, and make
the hook safe to run again.

```python
# my_app/tests/setup.py
import frappe


def before_tests():
    frappe.clear_cache()
    if not frappe.db.exists("Company", "Test Co"):
        frappe.get_doc({"doctype": "Company", "company_name": "Test Co",
                        "default_currency": "EUR"}).insert()
    frappe.db.commit()
```

An app that builds on ERPNext usually needs the setup wizard to have run. Call the ERPNext test
setup helper from the hook instead of creating the same records by hand.

Keep everything else in the tests. A record that only one test needs belongs in that test, or in
a test-record file, where the reader can see it next to the assertion that depends on it.

Do not depend on the order of apps. The hook of another app may or may not have run when yours
runs, so read what you need and create it when it is missing.

## Rules

No rule in the knowledge base covers this mechanism yet.
