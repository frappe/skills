---
id: M39
---
# M39 — Form event handlers

**What:** `frappe.ui.form.on(doctype, event, handler)` registers a handler for a form event, a
field change, or a child table event. The same call takes a dict of handlers. `*` as the doctype
registers a handler for every form. `frappe.ui.form.off` removes handlers, and `cscript` is the
old style the framework still dispatches.

**Guards:** Handlers accumulate in a list per doctype and per event, so every registration adds
one and none replaces another. Dispatch runs the doctype handlers first, then the `*` handlers,
then the old-style `cscript` and `custom_` methods. `setup` handlers run at once and in order;
every other event runs its handlers one after the other through `frappe.run_serially`, so a
handler that returns a promise delays the ones behind it. A handler that throws is logged to the
console and the error is re-raised. `frappe.ui.form.off` empties the whole list for the event,
which removes the framework's own handler and every other app's.

## Good use

Register handlers, and let them accumulate. This is what makes several apps able to extend one
form.

```javascript
frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        frm.add_custom_button(__("Create Trip"), () => make_trip(frm));
    },
    customer(frm) {
        frm.set_value("branch", "");
    },
});
```

Write a handler that does not depend on another handler. Read `frm.doc`, not a value that another
handler is expected to have set, because the order follows the install order of the apps.

`refresh` runs on load, after every save and after every route back to the form. Keep it free of
server calls, and put a call that depends on a field in that field's own handler instead.

Set a value with `frm.set_value` so the form and the model stay in step. Code that writes onto
`frm.doc` has to refresh the field itself.

Do not call `frappe.ui.form.off`. To stop a core button or a core action, hide it or override the
specific behaviour, and leave the handler list alone.

Use `*` only for behaviour that really is about every form. A `*` handler runs on every form load
on the site.

## Rules

- A20 — A rule that must always hold does not live in a Client Script
- A21 — Add to a client-side registry. Do not replace what another app put there
- A38 — Every `frappe.call` target resolves to a whitelisted method that still exists
- B45 — Refresh the field after code changes `frm.doc`
