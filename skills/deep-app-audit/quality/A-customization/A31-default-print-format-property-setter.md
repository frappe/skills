---
id: A31
area: customization
mechanism: M19
---
# A31 — Set the app's print format as the default with a Property Setter on install

**Why:** An app that ships a print format but does not make it the default leaves every user on
the standard format. The user prints the wrong document and finds out from the recipient. A
hard-coded default in the app code has the opposite problem: the site cannot change it.

## Bad

The app ships `print_format/regional_invoice/regional_invoice.json` with `"standard": "Yes"` and
nothing else. Every Sales Invoice still prints with the standard format.

## Good

```python
# my_app/setup/install.py
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def after_install():
	make_property_setter(
		"Sales Invoice", None, "default_print_format", "Regional Invoice", "Data", validate_fields_for_doctype=False
	)
```

```python
# my_app/setup/uninstall.py
import frappe


def before_uninstall():
	frappe.db.delete(
		"Property Setter",
		{"doc_type": "Sales Invoice", "property": "default_print_format", "value": "Regional Invoice"},
	)
```

## Find

- `ls */print_format/*/*.json` and read `"standard"` and `"doc_type"`.
- `rg -n 'default_print_format' --type py` in the app.
- A print format that the app ships with no matching Property Setter is the finding.
- The mirror image: `rg -n 'default_print_format' --type py` with no matching delete in an
  uninstall hook.

## Confirm

A Property Setter with `doctype_or_field` set to `DocType` and `property` set to
`default_print_format` changes the default for the DocType. Meta applies it
(`frappe/model/meta.py`).

An app that ships a print format as an option, not as a replacement, is not a finding. Ask
whether the app intends the format to be the default.

A print format shipped as a fixture rather than as a standard file is a separate finding under
A09 and A40.

Removing the setter on uninstall is part of A10.
