---
id: M36
---
# M36 — `has_website_permission`

**What:** A portal page for a document asks `frappe.has_website_permission` whether the visitor
may see it. Two things can answer: a `has_website_permission` method on the controller, or the
`has_website_permission` hook for the doctype.

**Guards:** The controller method wins. When the document's class has the method, the framework
returns its result and never reads the hook. Otherwise it runs every hook registered for the
doctype and returns `False` at the first falsy result; the answer is `True` only when all of them
are truthy. When the document's class has no method and no hook is registered, the answer is
`False`, so a portal document is not reachable until one of the two exists. A document with
`ignore_permissions` set is allowed before either is read. The call goes through `frappe.call`
with `doc`, `ptype`, `user` and `verbose` as keyword arguments. The renderer for a missing page
runs the same check to decide between a 403 and a 404.

## Good use

Pick one of the two. Put the method on the controller when the app owns the doctype, because it
lives next to the document and is read with it. Use the hook when the app adds a portal view to
another app's doctype.

```python
class DeliveryTrip(Document):
    def has_website_permission(self, ptype, user, verbose=False):
        return self.driver == frappe.db.get_value("Driver", {"user": user}, "name")
```

Answer for the visitor in front of you. A portal visitor is usually a Website User with no desk
role, so the answer comes from a link between the document and the user: the customer, the
supplier, the contact, the driver.

Return a boolean on every path. `None` denies, which is safe but confusing to read, and a
handler that returns a truthy object for one branch and nothing for another is hard to reason
about.

Two hooks on one doctype both have to agree. An app that adds a second hook narrows what the
first app allowed and can never widen it.

## Rules

- A25 — A hook handler accepts every argument the call site passes
- A28 — A permission hook can only narrow a result, and only where the framework reads it
