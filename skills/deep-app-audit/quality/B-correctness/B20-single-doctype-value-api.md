---
id: B20
area: correctness
semgrep: {rules: [frappe-single-value-type-safety, frappe-set-value-semantics], coverage: partial}
---
# B20 — Read and write a Single DocType with the single-value API

**Why:** A Single DocType has no table. Its values live as strings in `tabSingles`. The general
value API needs a document name to find a row, and a Single has none. Passing `None` or the
doctype name as the name makes the call take a different path, and on develop that path is a
deprecated shim. A value read the wrong way arrives as a string, so a boolean test on it is
always true.

## Bad

```python
if frappe.db.get_value("Stock Settings", None, "allow_negative_stock"):
    ...  # "0" is a non-empty string, so this branch always runs
frappe.db.set_value("Stock Settings", "Stock Settings", "allow_negative_stock", 0)
```

## Good

```python
if cint(frappe.db.get_single_value("Stock Settings", "allow_negative_stock")):
    ...
frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)
```

## Find

- `rg -n 'get_value\([^,]+,\s*None\s*,' --type py`, and a call that passes the doctype
  name as the document name, such as `get_value("Stock Settings", "Stock Settings", ...)`.
- `rg -n 'set_value\([^,]+,\s*None\s*,' --type py`.
- `rg -n 'get_single_value\(' --type py` with no `cint` or `flt` around a Check or a numeric
  field.
- `rg -n 'db_set\(' --type py` on a document that has not been inserted. `Document.db_set`
  returns without writing when `self.name` is `None`
  (`source:frappe/model/document.py:Document.db_set`).

## Confirm

`frappe.get_cached_doc("<Settings>")` is correct and returns typed values through the
controller. `frappe.db.get_single_value` casts the value from version 16 on; on older versions
the caller must cast. A `set_value` call with `None` as the name on a doctype that is **not**
Single returns silently on develop and writes nothing
(`source:frappe/database/database.py:Database.set_value`); on older versions the same call
updated every row of the table. Both outcomes are bugs, and neither raises.
