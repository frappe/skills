---
id: I01
area: info-disclosure
---
# I01 — Over-fetching helper endpoints

**Scope:** endpoints that return more than their name implies.

**Why:** the recurring shape is a "details" helper written for one screen and callable by
anyone.

## Find
- Whitelisted functions named `get_*_details`, `get_*_info`, `get_party_*`, `get_*_display`,
  `get_dashboard_data`, `get_context`, `get_*_summary`.
- For each: does it return a whole document, a joined set of documents, or a computed set of
  fields? Does it filter fields by `permlevel`? Does it check permission on every doctype it
  touches, or only the primary one?
- Endpoints returning lists where a single record was requested.
- `frappe.get_doc(...).as_dict()` returned wholesale — cross-reference `A01`.

## Confirm
- Enumerate the returned fields explicitly. "Returns the party details" is not a finding
  description; "returns `bank_account`, `tax_id`, and `credit_limit`" is.

## Report
Endpoint, caller role, field list leaked.
