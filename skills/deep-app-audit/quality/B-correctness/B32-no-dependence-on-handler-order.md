---
id: B32
area: correctness
mechanism: M12
---
# B32 — A handler must not depend on the run order of another handler

**Why:** The framework runs the controller method first, then every `doc_events` handler in
installed-app order, then notifications, webhooks and Server Scripts. App order changes when an
app is installed or reordered. A handler that reads a value another handler computes gets the
old value, or `None`, on a bench where the order differs. A handler that writes a field the
controller computes later is overwritten.

## Bad

```python
# hooks.py
doc_events = {"Sales Invoice": {"before_validate": "my_app.tax.set_tax_amount"}}

def set_tax_amount(doc, method=None):
    doc.custom_levy = flt(doc.total_taxes_and_charges) * 0.02
    # total_taxes_and_charges is computed later, in the standard validate
```

## Good

```python
# hooks.py
doc_events = {"Sales Invoice": {"validate": "my_app.tax.set_tax_amount"}}

def set_tax_amount(doc, method=None):
    # doc_events handlers run after the controller method for the same event
    doc.custom_levy = flt(doc.total_taxes_and_charges) * 0.02
```

## Find

- `rg -n 'doc_events' -A 40 hooks.py`, then for each handler list the fields it reads and check
  where the standard controller sets them.
- `rg -n 'before_validate' -A 15 --type py` for a handler that reads a derived total, a tax
  amount, a status, or a name.
- Two handlers from the same app on one event where one reads what the other writes.
- `rg -n 'override_doctype_class' -A 5 hooks.py` combined with a `doc_events` handler on the
  same doctype.

## Confirm

`Document.hook` runs the controller method first and the hooked handlers after it
(`source:frappe/model/document.py:Document.hook`), so a handler on `validate` sees what the
standard `validate` computed. That order is fixed and may be relied on. What may not be relied
on is the order between two apps, and the order between two events. `before_validate` is for
filling a missing input. `validate` is for checking and for deriving from a computed value.
A handler that needs a value another handler in the same app produces must call that code
directly instead of hooking twice.
