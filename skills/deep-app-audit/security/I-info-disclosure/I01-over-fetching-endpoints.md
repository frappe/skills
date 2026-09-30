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
- **Classify what came back** (`_framework-guards.md` section 7). Data of another party is
  Moderate or higher. Tenant configuration, such as an account or category name, is Low.
  Universal reference data, such as a country, a timezone, or a conversion factor, is not a
  finding.
- **Does the caller have it already?** When each doctype that the endpoint reads grants `read`
  at permlevel 0 to an automatic role of the caller, the response is public by design.
  `.entry_points[].touches_only_public_doctypes` in the inventory marks these. A field at
  permlevel above 0 in the response is still a finding.
- **The body decides the verdict, not the status.** Name the value from a record that the caller
  must not read. An empty 200, or only the records of the caller, is an acquittal. Compare with
  `/api/resource/<DocType>/<name>` in the same session: a 200 there means no boundary is crossed.

## Report
Endpoint, caller role, field list leaked, the value seen, and what the permissioned route
returned in the same session.
