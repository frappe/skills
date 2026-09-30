---
id: M31
---
# M31 — Form dashboard data

**What:** The connections panel of a form comes from `get_data` in
`<doctype>_dashboard.py`, next to the controller. The `override_doctype_dashboards` hook lets
another app change that data for a doctype it does not own.

**Guards:** Meta loads the module and calls `get_data` only when the doctype is not custom, and
an `ImportError` leaves the data empty. The DocType Link rows of the doctype are added next, so
they appear even when there is no dashboard file. The hook then runs, also for standard doctypes
only, and it is called with `data=` as a keyword argument. The framework replaces the whole
dashboard with what the handler returns, so a handler that returns nothing leaves an empty
dashboard.

## Good use

An app that adds a doctype which links to another app's document declares that connection in
its own dashboard file, and adds the reverse connection with the hook.

```python
# hooks.py
override_doctype_dashboards = {"Sales Order": "fleet.dashboards.sales_order_dashboard"}

def sales_order_dashboard(data):
    data["transactions"].append({"label": _("Fleet"), "items": ["Delivery Trip"]})
    return data
```

The handler takes the data, adds to it, and returns it. Adding to the existing groups keeps
every other app's entries, which a handler that builds a fresh dict would drop.

A doctype created in the desk with `custom=1` gets no dashboard file and no hook run. Its
connections come from its DocType Link rows only, which a user can add on the DocType form.

## Rules

- A26 — A hook handler returns what the call site expects
- A30 — Do not ship code for a DocType created with `custom=1`
