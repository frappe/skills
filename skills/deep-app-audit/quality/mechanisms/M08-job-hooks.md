---
id: M08
---
# M08 — Job hooks

**What:** `execute_job` wraps every background job. `before_job` runs first, with `method`,
`kwargs`, and `transaction_type="job"`. `after_job` runs in the `finally` block, with `method`,
`kwargs`, and `result`. They give an app one place to set job-scoped state and one place to
record how a job ended.

**Guards:** Both are called through `frappe.call`. The job body commits on success and rolls back
on failure, both before `after_job` runs, so `result` is `None` for a job that raised, and the
transaction is already closed. A job that hits a deadlock or a lock timeout is retried up to five
times; `before_job` runs again for each attempt. `after_job` also runs when the job raised, so the
handler must not assume success. `frappe.local.job.after_job` is a per-job callback manager and
runs after the hooks.

## Good use

Use `before_job` for job-scoped state, the same way `before_request` is used for request-scoped
state.

```python
# my_app/jobs.py
import frappe


def before_job(method, kwargs, transaction_type):
    frappe.local.my_app_job_started = frappe.utils.now()
```

Use `after_job` for accounting: a duration, a counter, a log row. Read `result` defensively,
because it is `None` when the job failed.

```python
# my_app/jobs.py
def after_job(method, kwargs, result):
    if not method.startswith("my_app."):
        return
    frappe.monitor.add_data_to_monitor(my_app_job=method)
```

Return early for the jobs the app does not own. Every job of every app on the site pays the cost
of both hooks.

Do not commit or roll back in either hook. The framework has already decided the outcome of the
transaction by the time `after_job` runs, and a commit there writes work the framework meant to
discard.

Do not retry the job from the hook. Raise `frappe.RetryBackgroundJobError` from the job itself
when a retry is wanted; the retry logic lives in `execute_job` and counts attempts.

## Rules

- A25 — A hook handler accepts every argument the call site passes
- B44 — Do not keep site or request state at module or class scope
- B40 — An optional step must not fail the main flow, and a swallowed failure must be logged
