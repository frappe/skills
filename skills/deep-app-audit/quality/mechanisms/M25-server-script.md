---
id: M25
---
# M25 — Server Script

**What:** A Server Script record holds Python that runs without a deploy. The `script_type`
field decides where it runs: DocType Event, Scheduler Event, Permission Query, API, or
Workflow Task.

**Guards:** Every type runs through `safe_exec`, which needs `server_script_enabled` in
`common_site_config.json` and compiles the script with RestrictedPython against a fixed set of
globals. The guards then differ by type. A DocType Event script runs with
`restrict_commit_rollback`, which removes `frappe.db.commit`, `frappe.db.rollback` and
`frappe.db.add_index` from its globals. A Scheduler Event, API, Permission Query or Workflow
Task script keeps all three. DocType Event scripts do not run at all while `in_install` or
`in_migrate` is set. An API script is matched before the dotted path is resolved, so a script
whose `api_method` equals an existing whitelisted path shadows that Python method for every RPC
caller. A Permission Query script appends its `conditions` string after the conditions from the
`permission_query_conditions` hooks.

## Good use

A Server Script belongs to a site, in the same way a Client Script does. It suits a rule that
one site needs, that an administrator must be able to read and switch off, and that no test
covers.

Write the script against `doc` and return nothing. The event names map onto the document
lifecycle, so "Before Save" is `validate` and "After Save" is `on_update`.

```python
if doc.grand_total > 100000 and not doc.customer_po_no:
    frappe.throw(_("Purchase order number is required above 100000"))
```

A Scheduler Event, API or Workflow Task script can commit, so it must own its transaction the
way any job does: commit at a batch boundary, and let an exception roll the work back.

Give an API script a method path that no Python method uses. A path that collides takes the
call away from the app that owns it, and nothing reports the collision.

An app's own logic is code, not a record. A Server Script has no version control, no test, no
review and no migration path, and it cannot be reached from Python. Install and migrate code
cannot use it at all, because DocType Event scripts are muted in both.

## Rules

- A22 — Ship an app's logic as app code, not as a Server Script record
- A23 — Install, migrate, and patch code cannot rely on Notifications, Webhooks, or Server Scripts
- B01 — Do not commit or roll back inside document lifecycle code
- B35 — A validation must run in every path that can change the data it protects
