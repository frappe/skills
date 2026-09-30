# H01 — Mass assignment / over-posting

**Scope:** bulk field writes from a request payload.

**Why:** a write that accepts a full field dict lets the caller set fields the form never shows,
including permission and IP-restriction fields.

## Find
- `rg -n "doc\.update\(|\.update\(frappe\.form_dict|get_doc\(json\.loads|update_doc|set_value" --type py`
- Whitelisted methods that accept a dict and apply it to a document without a field allowlist.
- `frappe.client.set_value` and `bulk_update` reachability per doctype.
- Fields that must never be client-writable: `owner`, `modified_by`, `docstatus`, `amended_from`,
  `naming_series` after creation, workflow state, `is_private`, role tables, price/amount
  fields on submitted docs, `user_type`, `enabled`.
- `permlevel` and `read_only` fields — are they enforced on the server or only in the UI?

## Confirm
- `read_only: 1` in the DocField is a UI hint; the server-side enforcement is `permlevel` plus
  `set_only_once` plus `allow_on_submit`. Check which actually applies.

## Report
List the writable-but-shouldn't-be fields per doctype.
