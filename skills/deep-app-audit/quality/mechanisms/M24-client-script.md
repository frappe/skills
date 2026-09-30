---
id: M24
---
# M24 — Client Script

**What:** A Client Script record holds JavaScript for one doctype and one view. Meta joins the
enabled Form scripts of the doctype into `__custom_js` and the enabled List scripts into
`__custom_list_js`, ordered by creation date.

**Guards:** A Form script runs after the standard doctype JavaScript and after every
`doctype_js` file, so it can override what an app registered. It does not run at all when the
form is opened through a DocType Layout, because the layout supplies its own script instead. A
List script runs last among the list assets, after `__list_js`, and it is not affected by a
layout. A script whose module is disabled is left out. A Form script that throws is caught and
reported in a message box; a List script that throws is not caught.

## Good use

A Client Script is a site's tool, not an app's. It suits a change that belongs to one site and
that a user must be able to read and switch off: a filter on a link field, a message on a
button, a hidden section for one company.

Keep the script to presentation. The desk form is one of many writers. The REST API, a data
import, a background job and a mobile client all reach the same document without loading any
JavaScript, so a rule enforced in a Client Script is not enforced.

Register handlers with `frappe.ui.form.on`. Handlers accumulate, so a Client Script adds to what
the app already registered and never needs `frappe.ui.form.off`.

```javascript
frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        frm.set_query("project", () => ({ filters: { status: "Open" } }));
    },
});
```

A site that runs a DocType Layout for the doctype loses its Form Client Scripts. Move the code
into the layout's own client script, or take the layout away.

An app that needs the same behaviour on every site ships the JavaScript as a file through
`doctype_js`. A file is reviewed, versioned, and removed with the app.

## Rules

- A20 — A rule that must always hold does not live in a Client Script
- A21 — Add to a client-side registry. Do not replace what another app put there
- A38 — Every `frappe.call` target resolves to a whitelisted method that still exists
- B45 — Refresh the field after code changes `frm.doc`
