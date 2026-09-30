---
id: A15
area: customization
mechanism: M54
---
# A15 — A `scheduler_events` method path is stored state, not only code

**Why:** A Scheduled Job Type row keys on the method string. A rename that the app does not
follow through leaves the work undone, and the site gives no error, because a path that does not
resolve is skipped at sync with a console warning.

## Bad

```python
# my_app/hooks.py, before the rename
scheduler_events = {"daily": ["my_app.tasks.send_reminders"]}

# my_app/hooks.py, after the rename
scheduler_events = {"daily": ["my_app.tasks.reminders.send"]}
```

The module was moved. Nothing else changed. The app has no patch and no note.

## Good

```python
# my_app/hooks.py
scheduler_events = {
	"daily": ["my_app.tasks.reminders.send"],
	"cron": {"0 2 * * *": ["my_app.tasks.rates.refresh"]},
}
```

```python
# my_app/patches/v2_0/drop_old_scheduled_jobs.py
import frappe

OLD_METHODS = ["my_app.tasks.send_reminders"]


def execute():
	for method in OLD_METHODS:
		frappe.db.delete("Scheduled Job Type", {"method": method})
```

## Find

- `rg -n 'scheduler_events' hooks.py` and resolve every method string against the tree.
- `git log -p -- hooks.py | rg 'scheduler_events' -A 20` for method strings that were changed or
  removed without a matching patch.
- On a site: read every Scheduled Job Type row and resolve `method` with `frappe.get_attr`.

## Confirm

`sync_jobs` inserts rows for the merged `scheduler_events` and then calls `clear_events`, which
deletes every Scheduled Job Type row whose method is not in the merged hooks
(`frappe/core/doctype/scheduled_job_type/scheduled_job_type.py`). On develop a stale row is
removed at the next migrate, as long as the app stays installed and the row carries no
`server_script` and no `scheduler_event`.

The failure that stays on develop is the silent one: `insert_single_event` skips a method that
does not resolve, so the new row is never created and the work stops. Confirm by resolving each
path.

`sync_jobs` runs at install and at migrate. A `scheduler_events` change without a migrate has no
effect.

A row that a user disabled is not a finding. `clear_events` keeps rows that carry a
`scheduler_event` link.
