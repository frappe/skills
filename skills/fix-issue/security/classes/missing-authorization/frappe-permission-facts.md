# What frappe's permission APIs actually check

Read on frappe `develop` in October 2026, with version-15 differences noted. Search by function
name in your own bench — line numbers drift, and behaviour has been backported between majors.

| API | What it checks | Watch for |
|---|---|---|
| `frappe.get_all` | nothing — `ignore_permissions=True` | the most common sink in a missing-authorization report |
| `frappe.get_list` | role permission on **`select`**, User Permissions, `permission_query_conditions`, `if_owner`, shares. Raises `PermissionError` | `select`, not `read`. On a child DocType it denies everyone but Administrator. `limit` defaults to **unlimited** |
| `frappe.db.get_list` | the same as `frappe.get_list` | |
| `frappe.qb.get_query(..., ignore_permissions=False)` | the same set as `get_list` | defaults to `ignore_permissions=True`. The keyword does not exist on version-15's engine |
| `frappe.qb.from_()` / `frappe.db.sql` | nothing | |
| `frappe.has_permission(dt, ptype, doc=None, throw=False)` | the `frappe.*` wrapper: with `doc=`, runs `check_doctype_permission` first, then the record check including User Permissions and shares | without `doc=` it is doctype-level only. `throw=True` forwards `print_logs`, which can name a refused record's linked value. `frappe.permissions.has_permission` has **no** `throw` parameter |
| `doc.check_permission(ptype)` | record-level check on a loaded document, raises | |
| `frappe.get_doc(dt, name)` | nothing, unless `check_permission=True` is passed | |
| `run_doc_method` (calling a whitelisted Document method over HTTP) | loads the doc with a **read** check | a mutating method needs its own `self.check_permission("write")` |
| `doc.db_set` | nothing | |
| `doc.save()` / `insert()` / `submit()` / `cancel()` / `delete()` | the matching ptype | already guarded |
| `frappe.only_for(roles)` | the session user has one of the roles. Administrator always passes | |
| `frappe.is_whitelisted(fn)` | the function is whitelisted. Guest refused unless `allow_guest` | runs before the body, so Guest tests say little. Website Users pass it |
| `find_file_by_url(url)` | iterates every `File` row with that URL and returns the first the user may download (public, owner, shared, or readable attached document) | returns `None` when none is permitted — refuse on `None` |
| `frappe.throw_permission_error()` | raises the constant "not permitted" `PermissionError` | for a docname the method looked up itself. A caller-supplied docname uses `has_permission(..., throw=True)` or `check_permission`. At top level on develop and version-16, in `frappe.handler` on version-15 |
| `frappe.permissions.get_all_perms(role)` | the site's effective rows, Custom DocPerm included | use in patches instead of `get_meta().permissions` |
| `Meta.permissions` | shipped rows **while `in_patch` / `in_install`** | stale inside patches, and cached |
| `add_permission` / `update_permission_property` | write a rule — and first switch the DocType to Custom DocPerm via `copy_perms` | detaches the DocType from future JSON permission changes |
| `typing_validations` (annotations on whitelisted args) | annotated scalar types | a `dict` annotation checks only the container. A **string-valued `Literal[...]` is not validated at all**. Annotations narrow types, not values |

## Address and contacts

Address's two permission hooks (`address_and_contact.has_permission` and its query conditions) look
for Link fields to parties, but Address links parties through the `links` Dynamic Link child table,
so both hooks are no-ops. What actually gates Address is `if_owner: 1` on its `All` DocPerm row:
doctype-level `has_permission("Address")` is True for everyone, and only the `doc=` form refuses a
non-owner. A check against the wrong mechanism tests a control that passes for everybody.
