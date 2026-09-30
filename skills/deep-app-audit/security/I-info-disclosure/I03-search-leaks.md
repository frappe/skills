---
id: I03
area: info-disclosure
---
# I03 — Search and link-field leaks

**Scope:** every search surface.

**Why:** global search and link search skip User Permission filters.

## Find
- Global search: `frappe.search.web_search`, `frappe.desk.search.search_widget`,
  `search_link`, `get_names_for_mentions`, awesome-bar handlers.
- Does each apply `permission_query_conditions`, User Permissions, and `permlevel` field
  filtering? The `__global_search` table is a denormalised copy — check what is written into
  it and who can query it.
- Link-field queries with a custom `query` in the DocField — those bypass the standard path.
- Autocomplete for users, teams, and customers returning records the caller cannot read.
- Report/list `group_by` counts revealing the existence of unreadable records.

## Confirm
- Counts and titles both count as leaks. A search returning zero rows but a non-zero count is
  still an oracle.

## Report
Give the search query and the leaked titles.
