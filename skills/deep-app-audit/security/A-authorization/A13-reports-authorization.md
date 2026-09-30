---
id: A13
area: authorization
---
# A13 — Report and query-report authorization

**Scope:** Query Report, Script Report, prepared reports, and report filters.

**Why:** report execution accepts filters and column lists that skip the checks the list view
applies.

## Find
- `frappe.desk.query_report.run` and app wrappers: is `user` client-controllable? Is
  `ignore_prepared_report` or `are_default_filters` abusable?
- Report doctype rows: `ref_doctype`, `disabled`, `roles` child table. Is the role restriction
  enforced server-side on execution, or only in the UI listing?
- Whether the report `query` / `report_script` body is readable by any Desk user — the SQL
  itself discloses schema and sometimes credentials.
- Prepared Report: can a user download another user's prepared report by name?
- Report filters reaching SQL — cross-reference `B01`, but the authorization angle here is
  filters that widen scope (`company`, `employee`) past the caller's permission.

## Confirm
- Check both `run` and the background/prepared path; each applies its checks separately.

## Report
Name the report and the filter or parameter used.
