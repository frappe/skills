---
id: B37
area: correctness
---
# B37 — Give every ordered query a tie-breaker, and state the order you depend on

**Why:** Rows with the same sort value come back in whatever order the database chooses. A
paged list then repeats one row and drops another. A "next document" link jumps back and forth.
`creation` and `modified` collide often, because a bulk import or a bulk update writes many rows
in the same second.

## Bad

```python
def get_page(customer, start):
    return frappe.get_all(
        "Delivery Note",
        filters={"customer": customer},
        order_by="creation desc",
        start=start,
        page_length=20,
    )
```

## Good

```python
def get_page(customer, start):
    return frappe.get_all(
        "Delivery Note",
        filters={"customer": customer},
        order_by="creation desc, name desc",
        start=start,
        page_length=20,
    )
```

## Find

- `rg -n 'order_by\s*=' --type py` in the app, then keep every value with one column that is
  used with `start`, `page_length`, `limit` or `[0]`.
- `rg -n 'get_all\(|get_list\(' -A 8 --type py` with `limit=1` and no `order_by`.
- `rg -n 'frappe\.get_last_doc\(' --type py`. It orders by `creation desc` with no tie-breaker
  (`source:frappe/__init__.py:get_last_doc`).
- `rg -n 'get_all\(|get_list\(' -A 8 --type py` that reads the first row and has no `order_by`
  at all. The default order is not part of the contract.

## Confirm

An order on a unique column, such as `name`, needs no tie-breaker. A query whose result is
summed or counted does not depend on order. The finding is a query whose caller treats the
order as meaningful.

The default sort changed from `modified desc` to `creation desc` in version 16 for
`frappe.get_all`, `frappe.get_list`, `frappe.db.get_value`, `frappe.db.get_values` and
`frappe.qb.get_query`. Code that relied on the old implicit order changed meaning at that
upgrade. State the order explicitly, so the code does not depend on the default at all.
