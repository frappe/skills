---
id: H03
area: business-logic
---
# H03 — Financial and quantity validation

**Scope:** money, quantity, and entitlement values that cross a trust boundary.

**Why:** amount, price, and subscription checks done only on the client let the user name their
own price.

## Find
- Payment initiation endpoints: is the amount taken from the request or recomputed from the
  referenced document server-side?
- Payment gateway callbacks/webhooks: signature verification, amount and currency matched back
  to the order, replay protection, idempotency.
- Discounts, prices, tax rates, and currency conversion accepted from the client.
- Negative or zero quantities, negative amounts, and quantities exceeding the source document.
- Entitlement checks: plan/subscription/feature gates enforced server-side, not just in the UI.
- Credit-limit, stock, and balance checks that read a value and act on it later
  (cross-reference `H04`).

## Confirm
- The test is always: can the client change the number that ends up in the ledger?

## Report
State the monetary impact in one line.
