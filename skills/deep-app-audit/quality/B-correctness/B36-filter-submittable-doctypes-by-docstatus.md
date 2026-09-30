---
id: B36
area: correctness
---
# B36 — Filter a submittable doctype by docstatus

**Why:** A query on a submittable doctype returns drafts, submitted documents and cancelled
documents together. A total that includes a cancelled invoice is wrong. A duplicate check that
counts drafts blocks a valid entry. The error is invisible on a new site, because no document
has been cancelled yet, and it appears months later on a site that cancels documents.

## Bad

```python
def get_outstanding(customer):
    rows = frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer},
        fields=["outstanding_amount"],
    )
    return sum(flt(row.outstanding_amount) for row in rows)
```

## Good

```python
def get_outstanding(customer):
    rows = frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer, "docstatus": 1},
        fields=["outstanding_amount"],
    )
    return sum(flt(row.outstanding_amount) for row in rows)
```

## Find

- `rg -n 'frappe\.(get_all|get_list|db\.get_values|db\.count)\(' -A 6 --type py` in the app,
  then check whether the doctype has `"is_submittable": 1` and whether the filters name
  `docstatus`.
- `rg -n 'frappe\.db\.sql\(' -A 8 --type py` for a query on a submittable table with no
  `docstatus` condition.
- `rg -n 'frappe\.db\.exists\(' --type py` on a submittable doctype.
- `rg -n 'docstatus\s*[<!]' --type py`. `docstatus < 2` includes drafts, which is right for a
  link check and wrong for a total.

## Confirm

A query that reports every state on purpose, such as a list view or an audit report, is
correct. A query on a doctype that is not submittable has no `docstatus` to filter. The right
value depends on the question: `1` for anything that counts, `("<", 2)` for a link or
duplicate check, `("!=", 2)` where a draft also matters. Use the `DocStatus` constants rather
than the literals. A `docstatus` filter on a child table must name the parent's docstatus, not
the child's.
