---
id: A22
area: customization
mechanism: M25
---
# A22 — Ship an app's logic as app code, not as a Server Script record

**Why:** A Server Script is a database row. It has no version control, no test, no review, and no
diff. It does not run during install or migrate, so any behaviour that depends on it is missing
exactly when a site is set up or upgraded. It is also the largest single group of customization
incidents.

## Bad

```python
# my_app/hooks.py
fixtures = [{"dt": "Server Script"}]
```

The app ships its validation as a Server Script fixture on Sales Invoice.

## Good

```python
# my_app/hooks.py
doc_events = {"Sales Invoice": {"validate": "my_app.accounts.validate_permit"}}
```

```python
# my_app/accounts.py
import frappe
from frappe import _


def validate_permit(doc, method=None):
	if not doc.myapp_permit_no:
		return
	if not frappe.db.exists("Permit", doc.myapp_permit_no):
		frappe.throw(_("Permit {0} does not exist.").format(doc.myapp_permit_no))
```

## Find

- `rg -n 'Server Script' hooks.py` inside `fixtures`.
- `ls fixtures/server_script.json`.
- On a site: Server Script rows whose `module` names an app, or whose script references an app's
  DocTypes or fieldnames.

## Confirm

`run_server_script_for_doc_event` returns early when `frappe.flags.in_install` or
`frappe.flags.in_migrate` is set
(`frappe/core/doctype/server_script/server_script_utils.py`). A Server Script never runs during
an install, a migrate, or the setup wizard. Logic a site needs at those moments must be app code.

DocType Event scripts run with `restrict_commit_rollback=True`, which removes `commit`,
`rollback`, and `add_index` from the sandbox (`frappe/utils/safe_exec.py`). API and Scheduler
scripts do not, so a commit in one of those is real.

Server Scripts need `server_script_enabled` in the common site config. An app that depends on a
Server Script does not work on a bench where the flag is off, and the flag is off by default.

A Server Script written by a site administrator for that one site is the correct use of the
mechanism. The finding is an app that ships one.
