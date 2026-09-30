---
id: B31
area: correctness
mechanism: M11
---
# B31 — Lifecycle code must not read request state

**Why:** A document is saved from a web request, from a background job, from a patch, from a
data import, from a bench command and from a test. Only the first of those has a request.
`frappe.local.request` and `frappe.form_dict` are empty everywhere else. Code in `validate` that
reads them raises during migrate or during a scheduled job, and the failure blocks a flow that
has nothing to do with the customization.

## Bad

```python
def set_source_channel(doc, method=None):
    doc.source_channel = frappe.local.request.headers.get("X-Channel")
```

## Good

```python
def set_source_channel(doc, method=None):
    if doc.source_channel:
        return
    doc.source_channel = doc.flags.source_channel or "Desk"

# the caller that has the request sets the flag before it saves
def create_from_api(payload):
    doc = frappe.get_doc(payload)
    doc.flags.source_channel = frappe.get_request_header("X-Channel") or "API"
    doc.insert()
```

## Find

- `rg -n 'frappe\.local\.(request|form_dict|response|request_ip)' --type py` inside a lifecycle
  method, a `doc_events` handler, or a scheduled method.
- `rg -n 'frappe\.form_dict' --type py` outside a whitelisted method.
- `rg -n 'frappe\.session\.user' --type py` in code that also runs from the scheduler. Scheduled
  jobs run as Administrator (`source:frappe/utils/background_jobs.py:execute_job`).
- `rg -n 'frappe\.request' --type py` in Server Script records of type `DocType Event`.

## Confirm

`frappe.session.user` is always set, so reading it is not a crash, but it is `Administrator` in
every scheduled job and `Guest` in a portal request. Ownership derived from it is wrong in those
paths. `frappe.get_request_header` returns `None` outside a request instead of raising, so it is
the safer read when the value is optional. The fix is to pass the value in, on a flag or on a
field, from the caller that has it.
