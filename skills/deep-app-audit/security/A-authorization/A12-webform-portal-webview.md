# A12 — Web Form, portal, and web view authorization

**Scope:** the portal-facing document surface.

**Why:** web forms and portal views use different permission defaults from the desk, and are
reachable by Website Users and Guests.

## Find
- Web Form definitions: `login_required`, `allow_edit`, `allow_multiple`, `apply_document_permissions`,
  and which fields are exposed. Can a user edit someone else's submission by supplying `name`?
- `has_website_permission` hooks — registered, and non-trivial?
- Web view / `/<doctype>/<name>` routes: `frappe.website.doctype.web_page`, `get_context`
  implementations that put the whole `doc` into the template context.
- Portal sidebar and list views (`portal_menu_items`) — do they filter by party?
- Print / PDF routes reachable with just a document name.

## Confirm
- Rendering only some fields in the template does not help if the whole doc is serialised
  into `frappe.boot` or a JSON island in the page.

## Report
Include the exact portal URL.
