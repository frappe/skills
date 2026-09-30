---
id: B17
area: correctness
---
# B17 — Coerce a value where it enters the system

**Why:** The framework carries many values as strings. Form data, `frappe.form_dict`, a JSON
request body, a Single DocType value and a Custom Field property all arrive as text. Python
compares `"100" < 64` without an error and gives the wrong answer. A child row is a `Document`
from a controller and a plain `dict` from `frappe.get_all`, so `row.field` works in one caller
and raises in the other. Coercion at each use site is forgotten in one place, and that place is
the bug.

## Bad

```python
@frappe.whitelist()
def apply_discount(invoice, percent):
    doc = frappe.get_doc("Sales Invoice", invoice)
    if percent > 50:                      # str compared with int
        frappe.throw(_("Discount is too high"))
    doc.discount_percentage = percent     # a string is written to a Float field
    doc.save()
```

## Good

```python
@frappe.whitelist()
def apply_discount(invoice: str, percent: float):
    percent = flt(percent)
    if percent > 50:
        frappe.throw(_("Discount is too high"))
    doc = frappe.get_doc("Sales Invoice", invoice)
    doc.discount_percentage = percent
    doc.save()
```

## Find

- `rg -n 'frappe\.form_dict\.\w+\s*[<>=!+*/-]' --type py`.
- `rg -n '@frappe\.whitelist' -A 6 --type py` for a parameter used in arithmetic or a
  comparison with no `flt`, `cint`, `cstr` or `getdate`.
- `rg -n '\.get\("\w+"\)\s*[<>*/]' --type py` on a value that came from JSON or a form.
- `rg -n 'def \w+\(.*doc' -A 15 --type py` for a function that reads `doc.field` and is also
  called with a `dict` row from `frappe.get_all`. Use `row.get("field")` for both.
- DocType JSON with `"fieldtype": "Int"` on a field named `rate`, `amount` or `price`.

## Confirm

A value read from a typed column and used in the same function is already the right type. The
finding is a value that crosses a boundary: HTTP, JSON, Redis, a Jinja context, a child row
dict, or `tabSingles`. `frappe.utils` supplies `flt`, `cint`, `cstr`, `getdate` and
`get_datetime` for this. A type hint on a whitelisted method makes the framework
coerce the argument, so an annotated signature is the strongest form
(`source:frappe/utils/typing_validations.py:validate_argument_types`). From version 16 a Single
DocType value read with `db.get_value` is cast, so a comparison against `"1"` that used to work
now fails.
