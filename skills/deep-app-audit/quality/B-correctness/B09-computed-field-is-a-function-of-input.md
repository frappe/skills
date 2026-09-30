---
id: B09
area: correctness
mechanism: M11
---
# B09 — A computed field must be a function of stored input, not of itself

**Why:** `validate` runs on every save. `on_change` also runs on `db_set`. Code that reads a
field and writes the same field compounds its own output. The value drifts on each save. On a
submitted document the same pattern raises "not allowed to change after submit", because the
value changes every time the form loads.

## Bad

```python
def apply_handling_charge(doc, method=None):
    for row in doc.items:
        row.qty = row.qty * 1.1  # 100 -> 110 -> 121 -> 133 on each save
```

## Good

```python
# Base Qty is a custom field the user fills. Qty is derived from it.
def apply_handling_charge(doc, method=None):
    for row in doc.items:
        row.qty = flt(row.base_qty) * 1.1
```

## Find

- `rg -n '\.(\w+)\s*=\s*.*\.\1\b' --type py` in the app for an assignment whose right side
  reads the field on its left.
- `rg -n 'def (validate|before_save|before_validate|on_change)' -A 25 --type py`, then look for
  a read and a write of one field in the same body.
- Server Script records with `script_type = "DocType Event"` and a `doctype_event` of
  `Before Save` or `Validate` that assign a field from itself.
- `rg -n 'append\(' --type py` inside `validate` or `before_save` with no `self.set(table, [])`
  before it. See B10.

## Confirm

An accumulation that reads a different field is correct, for example `total = sum of rows`. A
field written once, guarded by `if self.is_new()` or `if not self.field`, does not compound but
does drift when the guard field is cleared. The test is one save followed by a second save with
no user edit: every value must stay the same. `frappe.db.set_value` and `doc.db_set` both run
`on_change`, so a handler on `on_change` that writes the document is the same shape
(`source:frappe/model/document.py:Document.db_set`).
