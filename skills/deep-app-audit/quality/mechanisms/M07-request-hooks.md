---
id: M07
---
# M07 — Request hooks

**What:** `before_request` runs at the end of request setup, after `frappe.connect` and after
`HTTPRequest`. `after_request` runs when the response is ready and receives `response` and
`request`. Together they let an app set request-scoped state and add a response header.

**Guards:** Both are called through `frappe.call`. `after_request` returns at once when
`frappe.local.initialised` is not set, so it does not run for a request that failed before the
site was initialised. `before_request` runs for every request of every site, including static and
unauthenticated ones. It runs before login for a request that authenticates itself, so
`frappe.session.user` is not yet the final user.

## Good use

Use `before_request` to put a value on `frappe.local` that later code reads.

```python
# my_app/request.py
import frappe


def before_request():
    frappe.local.my_app_trace_id = frappe.request.headers.get("X-Trace-Id")
```

Use `after_request` to add a header or to record a metric.

```python
# my_app/request.py
def after_request(response, request):
    if trace_id := getattr(frappe.local, "my_app_trace_id", None):
        response.headers["X-Trace-Id"] = trace_id
```

Scope the work. A hook that runs on every request must return early for the paths it does not
care about, and must not query the database on a path where core makes no query. The cost is
paid by every request on the site, including asset requests and health checks.

Do not commit and do not roll back. The request owns the transaction, and the framework commits
it after the response is built.

Do not raise for a request the hook does not own. An exception in `before_request` fails the
request, and a handler that means to block one endpoint blocks the whole site when its condition
is wrong.

Keep state on `frappe.local`, never at module scope. A worker process serves many sites and many
requests, so a module-level variable leaks from one request into the next.

## Rules

- A25 — A hook handler accepts every argument the call site passes
- B44 — Do not keep site or request state at module or class scope
