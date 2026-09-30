---
id: A32
area: customization
mechanism: M47
---
# A32 — A template reads data. Logic belongs in a `jinja` hook method

**Why:** Template rendering runs in a restricted environment. A template that calls controller
methods or reaches into Python objects breaks when that restriction tightens, and it breaks at
print time, in front of a customer. A named method registered through the `jinja` hook keeps
working and can be tested.

## Bad

```html
<!-- print format -->
{% set totals = doc.calculate_taxes_and_totals() %}
<p>{{ doc.get_billing_address().address_line1 }}</p>
<p>{{ frappe.get_doc("Customer", doc.customer).credit_limit }}</p>
```

## Good

```python
# my_app/hooks.py
jinja = {"methods": ["my_app.print_utils.get_billing_lines"]}
```

```python
# my_app/print_utils.py
import frappe


def get_billing_lines(invoice_name):
	"""Return the address lines for an invoice, as plain strings."""
	address = frappe.db.get_value("Sales Invoice", invoice_name, "customer_address")
	if not address:
		return []
	return frappe.db.get_value("Address", address, ["address_line1", "city"], as_dict=True)
```

```html
<!-- print format -->
{% set lines = get_billing_lines(doc.name) %}
<p>{{ lines.address_line1 or "" }}</p>
```

## Find

- `rg -n '\{\{\s*doc\.\w+\(' */print_format/**/*.json */templates/**/*.html`.
- `rg -n '\{\{\s*doc(\.\w+){2,}' ` for chained attribute access with no default filter.
- `rg -n 'frappe\.get_doc|frappe\.get_all|__import__' ` inside template files.
- `rg -n 'jinja\s*=' hooks.py` to see what the app already registers.

## Confirm

`get_jenv` builds a sandboxed environment and adds only the methods and filters the `jinja` hook
registers (`frappe/utils/jinja.py:get_jenv`). App templates shadow framework templates, because
the loader lists the apps in reverse order with frappe last.

A read of a plain field, a formatted value, or a helper such as `get_formatted` is not a finding.

A chained attribute access with no `default` filter is a separate, smaller finding: the template
raises when the link is empty. Both belong in the same review of the template.

The old `jenv` hook name is gone. An app that still uses it registers nothing.
