# Fix missing authorization in a Frappe app

A whitelisted function runs **as the caller**, with whatever the caller sends. The fix is a guard on
**the resource the function reads or writes** — not the DocType that owns the file — chosen by the
**sink**, plus the **DocPerm rows** that keep every legitimate caller working. A guard shipped without
its rows turns a silent hole into a broken form on upgrade.

## Steps

### 1. Find the sink and its resource

Read the whitelisted body and every helper it calls until you reach the line that touches data:
`frappe.get_all`, `frappe.get_doc`, `frappe.db.get_value`, `frappe.qb`, `frappe.db.sql`, a file
read, `db_set`. Name the DocType (and record) that line exposes. That is the guard target.

Writes that go through the document layer — `doc.save()`, `insert()`, `submit()` — already check
permissions, so judge each sink by what it calls: a whitelisted *read* through `get_all` is
unguarded, while a `doc.save()` with no check in the body is guarded.

Done when: each sink in the call tree has a named target DocType and, where the caller picks the
record, the request argument that picks it.

### 2. Choose the guard by sink

| Sink | Guard |
|---|---|
| `frappe.get_all(dt, filters=<request>)` | **`frappe.get_list`** — it applies role permissions, User Permissions, `permission_query_conditions`, `if_owner` and shares, and raises by itself. A role-level `has_permission` in front of `get_all` still lets a user restricted to company A read company B |
| `frappe.get_doc` / `db.get_value` / `get_lazy_doc` on a request name | `frappe.has_permission(dt, ptype, doc=name)` before, or `doc.check_permission(ptype)` after loading. Without `doc=` the check is doctype-level only |
| A `frappe.qb` query you cannot turn into `get_list` | `frappe.qb.get_query(dt, ..., ignore_permissions=False)` — it applies the same conditions as `get_list`. It skips them only by default |
| A **child** DocType (`istable`) queried directly | **two steps**: `get_list` the parent with `pluck="name"`, then bound the child query by `parent IN names`. `get_list` on a child denies everyone but Administrator, so a test suite run as Administrator stays green |
| A caller-supplied `file_url` | `file = frappe.core.doctype.file.utils.find_file_by_url(url)`. `raise frappe.PermissionError` if it is `None`. It tries every File row with that URL, where `frappe.get_doc("File", {"file_url": url})` picks one arbitrarily |
| A pure role gate, with no record | `frappe.only_for("System Manager")` |
| A mutating whitelisted **Document method** | `self.check_permission("write")` as its first line — `run_doc_method` checks only **read**, and `db_set` checks nothing |
| `ignore_permissions` exposed as a whitelisted argument | remove the parameter. Pass a literal `False` inward |
| A state change reachable over GET | also add `methods=["POST"]` — see [classes/input-and-request-handling.md](input-and-request-handling.md) |

**Pick the ptype:** `select` for a picker or helper that fetches a chosen record's name or one value
into a form. `read` when the endpoint returns the record's contents. `write` / `create` / `submit` or
`only_for` for a mutation. Prefer `select` where it works — it does not widen exposure.

**`get_list` authorises the DocType on `select`, not `read`.** Converting to `get_list` silently lets
every role with only `select` through, even if you meant `read`. When the construct changes,
recompute who passes. A filter on a *child* field through a parent `get_list` requires `read`, which
restores read semantics where you want them.

**Choose the record check by where the docname comes from.**

*A docname the caller supplied* is checked with frappe's own refusal, which names only what the
caller sent:

```python
name = cstr(name)
if not name:
	frappe.throw(_("Name is required"))
frappe.has_permission(doctype, doc=name, ptype=ptype, throw=True)
```

or, when the method loads the document anyway:

```python
doc = frappe.get_doc(doctype, cstr(name))
doc.check_permission(ptype=ptype)
```

`cstr` stops a dict or list being treated as a document: `typing_validations` checks an annotated
scalar, but `filters: dict` guarantees only the container, and `filters["name"] = ["like", "%"]`
widens a query after one record was authorized. The `not name` test stops `doc=""` from falling back
to a doctype-level check. Loop the same check over each name in a caller-supplied list.

*A docname the method looked up itself* — a `frappe.db.get_value`, a link read from another record,
a loop over fetched rows — is refused with the constant `frappe.throw_permission_error()`
(`frappe.throw(_("Not permitted"), frappe.PermissionError)` where the line's frappe lacks it):

```python
fund = frappe.db.get_value("Loan Settings", None, "default_fund")
if not frappe.has_permission("Fund", "read", doc=fund):
	frappe.throw_permission_error()
```

The caller never sent that name, so the refusal must not reveal it. `throw=True` forwards
`print_logs`, and for a user fenced by User Permissions the message names the refused record and
its linked value ("…linked to <DocType> 'X'").

Hand-written refusals around a permission check (`if not frappe.has_permission(...):
frappe.throw(_("Not permitted"))`) are replaced by one of the two forms above. Input validation —
a missing name, an unknown DocType, an unknown sort key — is not a permission check and keeps its
own `frappe.throw`.

**Put the check in the whitelisted body**, not in an internal helper or a validator that other code
paths also call.

Done when: every sink from step 1 has a guard from this table, with a chosen ptype.

### 3. Compute who loses access

```
losers = roles with write or create on each CALLER form's DocType
       − roles holding the guard ptype on the guard target DocType
```

Read both sides from the DocType JSON files at the target branch. Find callers through the JS that
calls the endpoint (`frappe.call`, `frm.call`, link-field `get_query`), and separately through portal
`get_context` pages and other apps. Every role left in the set gets a `PermissionError` after
upgrade.

Run this for a **proposed** fix too, before recommending it. A fix that reads right can still deny
most of the roles that need it.

Done when: the loser set is computed and each loser is closed in step 4, or the decision to leave one
is written down with the person who owns the module.

### 4. Ship the DocPerm rows with the guard

Grant the guard ptype (at least `select`. `read` if the endpoint returns contents) to every loser,
**in the same PR** as the guard. Bump the DocType's `modified` with every JSON permission edit, and
ship a Custom DocPerm mirror patch for sites that already customised the DocType, which read only
their Custom DocPerm rows. Ship the rows, the patch and the guard on **every release line**. Procedure
and rules: [docperm-shipping.md](missing-authorization/docperm-shipping.md).

If the row belongs to a DocType another app ships, the row must land there first: hold the check and
escalate the ordering, because a check without its row is an outage for every loser. If granting would widen exposure too far, change the caller to send
the reference document and check that instead.

Done when, on every release line: every loser from step 3 holds the guard ptype on both sites of the
two-site regression.

### 5. Prove it with the regression matrix

Run the endpoint before and after the fix as each identity in
[regression-matrix.md](missing-authorization/regression-matrix.md) — at minimum an entitled role, each loser, a
select-only role, a role-less System User, a **Website User**, and a user fenced by a User Permission.
Compare **return values**: a guard that silently narrows a result raises no exception and still fails
a user. Run it inside the two-site regression
([verify.md](../verify.md) step 4).

Done when, on every release line: the security rows are refused, the entitled rows return the same
data as before, and the fenced user sees only their own records.

## References

- [docperm-shipping.md](missing-authorization/docperm-shipping.md) — JSON rows, the `modified` bump, Custom
  DocPerm mirror patches, and rows on another app's DocType.
- [regression-matrix.md](missing-authorization/regression-matrix.md) — the identities, why each matters, and the
  two-site rule.
- [frappe-permission-facts.md](missing-authorization/frappe-permission-facts.md) — what each frappe permission
  API really checks. Read before arguing a path "is already guarded".
- Checking a branch or release for the fix: [verify.md](../verify.md).
