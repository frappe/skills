---
id: M54
---
# M54 — Scheduler events

**What:** `scheduler_events` declares the periodic jobs of an app. The keys are `all`, `hourly`,
`daily`, `weekly`, `monthly`, their `_long` variants, and `cron`. Every key but `cron` holds a
list of dotted method paths. `cron` holds a dict of cron expression to list of method paths.
`sync_jobs` turns the merged declaration into Scheduled Job Type records on install and on
migrate.

**Guards:** A Scheduled Job Type row is keyed on the method string, so the dotted path is stored
state, not only code. A rename creates a new row and orphans the old one, together with its
`stopped` flag and its `last_execution`. `insert_single_event` resolves the path first: a method
that does not resolve is skipped with a yellow warning and the job silently never runs. Jobs are
collected from every installed app, disabled ones included, so that disabling an app does not
delete its rows; those rows are skipped at enqueue instead. Only the frequency and the cron
format of an existing row are updated on sync; every other field keeps the site's value. A job
runs in a background worker with its own transaction and no request context.

## Good use

The app declares the paths and keeps them stable.

```python
# hooks.py
scheduler_events = {
	"daily": ["my_app.tasks.expire_permits"],
	"cron": {"0 2 * * *": ["my_app.tasks.rebuild_permit_index"]},
}
```

```python
# my_app/tasks.py
import frappe


def expire_permits():
	names = frappe.get_all(
		"Permit", filters={"status": "Active", "valid_till": ["<", frappe.utils.today()]}, pluck="name", limit=500
	)
	for name in names:
		frappe.get_doc("Permit", name).set_expired()
```

The job takes a bounded batch. The next run takes the next batch. A job that reads every
matching row grows with the site and eventually runs longer than its own interval.

The job is a plain function that can be called from a test and from `bench execute`. It is
idempotent: a second run over the same rows changes nothing, because the filter no longer
matches them.

When a method must move, the app keeps the old path as a thin wrapper, or it ships a patch that
renames the `method` field of the Scheduled Job Type row.

## Rules

- A15 — A `scheduler_events` method path is stored state, not only code.
- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve.
- B08 — Give a repeatable endpoint or job a deduplication key.
