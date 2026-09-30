---
id: A14
area: customization
mechanism: M01
---
# A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve

**Why:** A hook path that does not resolve raises at the moment the framework reads it, which is
often a request or a migrate rather than a deploy. A scheduler path that does not resolve is
skipped with a warning, so the job silently never runs. A patch path that does not resolve stops
`bench migrate` for the whole site.

## Bad

```python
# my_app/hooks.py
doc_events = {
	"Sales Invoice": {"on_submit": "my_app.accounts.utils.push_to_portal"}
}
scheduler_events = {"daily": ["my_app.tasks.daily.sync_rates"]}
```

```
# my_app/patches.txt
[post_model_sync]
my_app.patches.v1_0.rename_permit_field
```

The module `my_app.accounts.utils` was renamed to `my_app.accounts.portal`. The patch module was
deleted after it ran on the developer's site.

## Good

```python
# my_app/hooks.py
doc_events = {
	"Sales Invoice": {"on_submit": "my_app.accounts.portal.push_to_portal"}
}
scheduler_events = {"daily": ["my_app.tasks.daily.sync_rates"]}
```

```
# my_app/patches.txt
[post_model_sync]
my_app.patches.v1_0.rename_permit_field
```

The patch module stays in the tree after it ran. A patch is never deleted, because other sites
have not run it yet.

## Find

- Collect every string value in `hooks.py` that contains a dot and no space.
- Resolve each against the app tree: the path before the last dot is a module, the last segment
  is an attribute.
- Every line in `patches.txt` that is not a section header, a comment, or an `execute:` line
  names a module with a `execute()` function.
- `rg -n 'scheduler_events' hooks.py`, then resolve each method string.

## Confirm

`frappe.get_attr` throws `AppNotInstalledError` when the first segment is not an installed app
(`frappe/utils/__init__.py:get_attr`). A path that names an optional app is a finding unless the
hook is registered under a guard.

`insert_single_event` calls `frappe.get_attr` and prints a yellow warning when it fails, then
returns (`frappe/core/doctype/scheduled_job_type/scheduled_job_type.py`). The job row is never
created. Nothing fails at run time, so this finding is invisible without the check.

A path that resolves in the app's own tree but names a first-party app function is still a
finding when that function is not part of the public surface. See A36.
