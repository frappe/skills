---
id: H04
area: business-logic
---
# H04 — Race conditions and idempotency

**Scope:** check-then-act sequences under concurrency.

**Why:** counters, coupons, and stock quantities updated without locking allow double spend.

## Find
- Counters and quotas: coupon usage, seat/enrolment limits, stock reservation, serial/batch
  allocation, invite-use counts, rate-limit counters.
- Read-modify-write on a document field without `for update`, a unique constraint, or an
  atomic DB operation.
- `frappe.db.get_value(...)` followed by `frappe.db.set_value(...)` on the same row.
- Naming: `make_autoname` collisions and duplicate-key handling under load.
- Idempotency of webhook and payment callback handlers — replayed callbacks.
- Background jobs enqueued more than once for the same document.

## Confirm
- Say what two concurrent requests produce. If the DB has a unique index that saves it, that
  is not a finding.

## Report
Moderate unless it yields money or access; then High.
