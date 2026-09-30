---
id: A06
area: customization
mechanism: M12
---
# A06 — Attach business logic to the transaction, not to the ledger entry it creates

**Why:** A ledger row is a projection of its transaction. Logic that edits the row makes the
document and the ledger disagree. Two standard reports on the same data then give two answers,
and no cancel path can undo the difference.

**Applies to:** an app that customizes ERPNext accounting or stock.

## Bad

```python
# my_app/hooks.py
doc_events = {
	"Stock Ledger Entry": {"before_insert": "my_app.stock.add_transit_allowance"}
}
```

```python
# my_app/stock.py
def add_transit_allowance(doc, method=None):
	doc.actual_qty = doc.actual_qty * 1.1
```

## Good

```python
# my_app/hooks.py
doc_events = {
	"Delivery Note": {"validate": "my_app.stock.set_delivered_qty"}
}
```

```python
# my_app/stock.py
def set_delivered_qty(doc, method=None):
	"""Ship 10 percent more than ordered to cover transit damage.

	`custom_ordered_qty` holds the input. `qty` holds the result, so the computation is
	idempotent across saves.
	"""
	for row in doc.items:
		row.qty = flt(row.custom_ordered_qty) * 1.1
```

## Find

- `rg -n '"(GL Entry|Stock Ledger Entry|Payment Ledger Entry|Serial and Batch Bundle|Bin)"' hooks.py`
  inside `doc_events` and `override_doctype_class`.
- In each handler, an assignment to `actual_qty`, `qty`, `debit`, `credit`, `rate`,
  `stock_value_difference`, or `valuation_rate`.
- Server Script records with `reference_doctype` in the same set.

## Confirm

A read-only handler on a ledger DocType is not a finding for this rule. It may still be a
performance finding, because a ledger handler runs once per line item of every voucher.

A handler that only stamps a reference or an audit field on the ledger row is a weak finding.
Ask whether the value can come from the transaction at report time instead.

A finding is strong when the handler writes a field that a standard report sums, or a field
that the cancel path reverses. Cancel rebuilds the ledger from the transaction, so the custom
value is lost on cancel and amend.

This rule is about a handler that edits a ledger row the framework created. Code that inserts,
updates or deletes the row itself is the larger failure, and it is A41.
