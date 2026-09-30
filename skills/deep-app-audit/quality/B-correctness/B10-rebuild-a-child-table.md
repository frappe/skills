---
id: B10
area: correctness
---
# B10 — Rebuild a generated child table instead of appending to it

**Why:** Code in `validate` or `before_save` that appends a generated row adds one more row on
every save. The table grows, the totals grow with it, and the document cannot be corrected from
the form because the user did not add the rows.

## Bad

```python
def add_default_taxes(doc, method=None):
    for tax in get_company_taxes(doc.company):
        doc.append("taxes", {"account_head": tax.account, "rate": tax.rate})
```

## Good

```python
def add_default_taxes(doc, method=None):
    if not doc.is_new():
        return
    doc.set("taxes", [])
    for tax in get_company_taxes(doc.company):
        doc.append("taxes", {"account_head": tax.account, "rate": tax.rate})
```

## Find

- `rg -n '\.append\("' -B 6 --type py` in the app. Keep every hit inside `validate`,
  `before_save`, `before_validate` or `on_update` that has no `set(<table>, [])` and no guard
  above it.
- `rg -n '\.append\(' --type py` in a `doc_events` handler on a doctype the app does not own.
- `rg -n 'extend\(' --type py` on a child table field.

## Confirm

An append driven by a user action, such as a whitelisted "add row" method, is correct. An
append guarded by a check for the row it is about to add is correct but is a check-then-act
race when two saves run in parallel; see B05. A rebuild loses user edits in the table, so
rebuild only a table the app owns end to end. Rows the framework generated carry no marker,
so the rebuild must be able to tell a generated row from a user row before it clears the table.
