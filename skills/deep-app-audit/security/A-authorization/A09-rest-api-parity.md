# A09 — REST API vs Desk parity

**Scope:** data reachable through the generic API that the Desk UI never exposes.

**Why:** the REST API exposes every doctype and method the desk uses. The UI hiding something is
not a control.

## Find
- `frappe.client.*` entry points: `get`, `get_list`, `get_count`, `get_value`, `set_value`,
  `insert`, `insert_many`, `submit`, `cancel`, `delete`, `bulk_update`, `rename_doc`,
  `validate_link`.
- App-level wrappers around those that relax a parameter.
- `/api/resource/<doctype>` behaviour for doctypes the app assumes are internal:
  `Singles`-backed settings, log doctypes, integration settings.
- Whether `permlevel` fields are stripped from generic API responses.

## Confirm
- Check `get_count` and `get_value` separately from `get_list` — each applies its
  checks through its own code path.
- A doctype with no `read` permission row is not automatically safe; check `All` and
  `if_owner`.

## Report
List doctype + endpoint pairs with the fields exposed.
