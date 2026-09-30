---
id: B40
area: correctness
---
# B40 — An optional step must not fail the main flow, and a swallowed failure must be logged

**Why:** A telemetry call, a notification, a cache warm-up and an external sync are optional.
Code that lets one of them raise blocks the save, the submit or the boot that the user asked
for. The opposite error is as bad: a bare `except: pass` hides a failure that nobody ever sees,
so the missing data is found weeks later with no traceback to work from.

## Bad

```python
class ShipmentRequest(Document):
    def on_submit(self):
        requests.post(get_tracking_url(), json=self.as_dict())  # blocks the submit

def sync_all():
    for name in get_pending():
        try:
            push(name)
        except Exception:
            pass  # no record that this ever happened
```

## Good

```python
from frappe.database.database import savepoint

class ShipmentRequest(Document):
    def on_submit(self):
        frappe.enqueue(
            "my_app.tracking.push", name=self.name, enqueue_after_commit=True
        )

def sync_all():
    for name in get_pending():
        with savepoint(catch=Exception):
            push_and_log(name)

def push_and_log(name):
    try:
        push(name)
    except Exception:
        frappe.log_error(title=f"Push failed for {name}")
        raise  # the savepoint above rolls back this one row only
```

## Find

- `rg -n 'except .*:\s*$' -A 2 --type py` followed by `pass` or `continue`.
- `rg -n 'frappe\.log_error\(' --type py` with a message and no traceback. `frappe.log_error`
  captures the traceback when it is called inside an `except` block.
- `rg -n 'requests\.(get|post|put)\(' --type py` inside a lifecycle method, a boot hook, an
  install hook or a permission hook.
- `rg -n 'get_hooks\(' --type py` in boot or permission code where a broken app's hook can
  raise.
- `rg -n 'except Exception as e' -A 3 --type py` where the handler prints `str(e)` and drops
  the traceback.

## Confirm

An exception that must stop the flow, such as a failed validation, belongs to the flow and is
not a finding. A narrow catch of one named exception, with a comment that says why, is correct.
The two questions are: does the main action still succeed when this step fails, and can an
engineer find the failure afterwards. A step that must succeed is not optional, and it belongs
inside the transaction, not inside a `try`.
