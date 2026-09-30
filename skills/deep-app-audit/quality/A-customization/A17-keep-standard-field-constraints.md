---
id: A17
area: customization
mechanism: M19
---
# A17 — Do not unset `reqd` or `read_only` on a standard field

**Why:** Core code reads standard fields without checking whether they are filled. A field that
core marks mandatory is a precondition of that code. Removing the constraint moves the failure
from a clear message at save time to a wrong number or a traceback later.

## Bad

```python
# my_app/setup/install.py
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def after_install():
	make_property_setter("Purchase Order Item", "item_code", "reqd", 0, "Check")
	make_property_setter("Sales Invoice", "grand_total", "read_only", 0, "Check")
```

## Good

```python
# my_app/setup/install.py
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def after_install():
	"""The customer does not use item codes. Give every line the service item and hide it."""
	make_property_setter("Purchase Order Item", "item_code", "default", "SERVICE-ITEM", "Data")
	make_property_setter("Purchase Order Item", "item_code", "hidden", 1, "Check")
```

## Find

- `rg -n 'make_property_setter\(' --type py` in the app, then keep hits whose property is
  `reqd`, `read_only`, `allow_on_submit`, `options`, `precision`, or `is_virtual`, and whose
  value turns the constraint off.
- `rg -n '"property":\s*"(reqd|read_only|allow_on_submit)"' fixtures/*.json */custom/*.json`.
- On a site: Property Setter rows where `property in ('reqd', 'read_only')` and `value = '0'`.

## Confirm

Customize Form refuses each of these changes on a standard field and returns `False` with a
message (`frappe/custom/doctype/customize_form/customize_form.py:allow_property_change`). Code
that calls `make_property_setter` bypasses that guard, and so does a Property Setter shipped as a
fixture or in a `custom/` folder. A finding here is always code or data, never the UI.

The same function refuses `allow_on_submit` on a standard field. `allow_on_submit` on a field
that carries an amount, a quantity, a party, a date, or a ledger account is a strong finding even
when the field is a Custom Field, because a submitted document is a closed record.

A Property Setter that turns a constraint on, rather than off, is A18, not this rule.
