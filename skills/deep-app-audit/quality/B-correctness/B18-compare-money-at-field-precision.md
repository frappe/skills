---
id: B18
area: correctness
---
# B18 — Compare money and quantity at the precision of the field

**Why:** A float carries a remainder that the user cannot see. Two amounts that print the same
are not equal in Python. A bare equality check on a total blocks a submit that should pass, or
lets an unbalanced voucher through. Rounding in the middle of a chain adds a second error on
top of the first.

## Bad

```python
def validate_allocation(doc):
    if doc.total_allocated != doc.grand_total:
        frappe.throw(_("Allocated amount must equal the grand total"))
```

## Good

```python
def validate_allocation(doc):
    precision = doc.precision("grand_total")
    if flt(doc.total_allocated, precision) != flt(doc.grand_total, precision):
        frappe.throw(
            _("Allocated amount {0} must equal the grand total {1}").format(
                doc.total_allocated, doc.grand_total
            )
        )
```

## Find

- `rg -n 'flt\([^,)]*\)\s*[=!]=\s*flt\([^,)]*\)' --type py`. Both sides without a precision.
- `rg -n '_amount\s*[<>=!]=|_qty\s*[<>=!]=|total\s*[<>=!]=' --type py` with no `flt` on either
  side.
- `rg -n '\bround\(' --type py` in accounting, stock or payroll code. `flt(value, precision)`
  is the framework form.
- `rg -n 'flt\(' --type py` applied more than once in one computation chain.
- DocType JSON with `"fieldtype": "Float"` on a field that holds money. Money is `Currency`.

## Confirm

An integer comparison, a comparison against zero on a value that is only ever set from an
integer, and a `>` or `<` test whose result does not change at the last decimal are not
findings. `doc.precision(fieldname)` reads the field's own precision and falls back to the
system default (`source:frappe/model/base_document.py:BaseDocument.precision`).
`frappe.get_precision(doctype, fieldname)` is the form outside a document. Round once, at the
end, at the precision of the field the result is written to.
