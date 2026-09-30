---
id: M34
---
# M34 — `has_permission` hook

**What:** The `has_permission` hook adds a controller-level permission check for one doctype, or
for every doctype under the `*` key. It runs after the role and user permission checks have
already granted the permission.

**Guards:** The hook can only deny. The framework collects the methods for the doctype, then the
methods under `*`, runs them in reverse order, and stops at the first result that is falsy,
returning that value as a boolean. When no method denies, the result is `True`. A handler that
falls off the end returns `None`, which is falsy, so it denies. The call goes through
`frappe.call` with `doc`, `ptype`, `user` and `debug` as keyword arguments.

The hook shapes a single-document check. It does not shape a list. A report view, a list view and
`frappe.get_all` do not run it, so a document the hook denies is still counted and still listed
unless a `permission_query_conditions` hook removes it as well.

## Good use

Use the hook for a rule that the permission model cannot express and that depends on the
document: a state, a date window, a value on a linked record.

```python
# hooks.py
has_permission = {"Delivery Trip": "fleet.permissions.delivery_trip_has_permission"}

def delivery_trip_has_permission(doc, ptype, user, **kwargs):
    if ptype != "write":
        return True
    return doc.status != "Completed"
```

Return `True` on every path the rule does not cover. A handler that only returns a value inside
one branch denies every other case, which takes the document away from users the site meant to
allow.

Keep the handler cheap. It runs once per document check, which includes every document the desk
opens and every document a bulk action touches.

A rule that must also hide the document from lists needs a `permission_query_conditions` hook
that expresses the same condition in SQL. The two are written together and tested together.

Register the handler under the doctype, not under `*`, unless the rule really is about every
doctype. A `*` handler runs for every permission check on the site.

## Rules

- A25 — A hook handler accepts every argument the call site passes
- A28 — A permission hook can only narrow a result, and only where the framework reads it
