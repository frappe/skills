---
id: M46
---
# M46 — Setup wizard hooks

**What:** An app shapes the first run of a site through the setup wizard. `setup_wizard_stages`
returns the stages and tasks the wizard shows and runs. `setup_wizard_complete` names a
function that runs after the stages. `setup_wizard_success` runs after the whole wizard.
`setup_wizard_exception` receives the traceback and the arguments when a stage fails.
`setup_wizard_requires` adds a script the wizard page loads. `setup_wizard_url` replaces the
built-in wizard with a route of the app's own.

**Guards:** `get_setup_wizard_url` uses `setup_wizard_url` only when no active app declares
`setup_wizard_stages` or `setup_wizard_complete`. Stage hooks therefore win over the URL, and
the two cannot be combined. The URL must be a route outside `/desk` and `/app`, because it
redirects the user out of desk. Stages are collected per app, in app order, and every task is
tagged with the app that supplied it. Frappe commits after every stage succeeds, so a stage
must not commit for itself. `handle_setup_exception` rolls the transaction back before it calls
the exception hooks.

## Good use

The app adds its own stage and lets the framework own the transaction.

```python
# hooks.py
setup_wizard_stages = "my_app.setup.wizard.get_stages"
setup_wizard_complete = "my_app.setup.wizard.after_setup"
```

```python
# my_app/setup/wizard.py
import frappe
from frappe import _


def get_stages(args):
	return [
		{
			"status": _("Setting up permits"),
			"fail_msg": _("Failed to set up permits"),
			"tasks": [{"fn": create_permit_types, "args": args, "fail_msg": _("Could not create permit types")}],
		}
	]


def create_permit_types(args):
	for name in ("Import", "Export"):
		if not frappe.db.exists("Permit Type", name):
			frappe.get_doc({"doctype": "Permit Type", "permit_type_name": name}).insert()
```

Each task creates records and nothing else. It does not commit and it does not roll back: a
failure must leave a clean site, and the framework rolls the whole wizard back.

An app that owns the whole first-run experience uses `setup_wizard_url` alone, on a portal
route, and declares no stage hooks. A bench that carries both never reaches the URL.

Every dotted path in these hooks is read while the site is still empty. A path that does not
resolve stops the setup of the site.

## Rules

- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve.
- B02 — Own the rollback when you catch an exception.
- B40 — An optional step must not fail the main flow, and a swallowed failure must be logged.
