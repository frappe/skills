---
id: A04
area: customization
mechanism: M13
---
# A04 — Use `regional_overrides` before a controller override

**Why:** A controller override takes the whole DocType from every other app. A regional
override replaces one function, keeps the rest of the class, and lets a second regional app
live on the same site.

**Applies to:** an app that changes ERPNext behaviour for one country or one tax regime.

## Bad

```python
# my_app/hooks.py
override_doctype_class = {"Sales Invoice": "my_app.overrides.sales_invoice.RegionalSalesInvoice"}
```

## Good

```python
# my_app/hooks.py
regional_overrides = {
	"Atlantis": {
		"erpnext.controllers.taxes_and_totals.get_itemised_tax_breakup_data": "my_app.taxes.get_itemised_tax_breakup_data"
	}
}
```

## Find

- `rg -n 'override_doctype_class' hooks.py` in an app whose name or module names a country.
- `rg -n '@erpnext.allow_regional' <bench>/apps/erpnext` lists every function that
  accepts a regional override.
- Compare the two lists. An override class whose only changed method has an `allow_regional`
  counterpart is a finding.

## Confirm

`allow_regional` reads `regional_overrides` for the company country and calls the last
registered override (`erpnext/__init__.py:allow_regional`). The region key is the country name,
not a country code.

A finding is real only when an `allow_regional` function covers the same behaviour. When no
such function exists, the override stays, and the app raises an issue upstream to ask for the
decorator.
