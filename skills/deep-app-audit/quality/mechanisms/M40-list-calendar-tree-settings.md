---
id: M40
---
# M40 — List, calendar and tree settings

**What:** Three client registries hold the per-doctype behaviour of the desk views:
`frappe.listview_settings[doctype]` for the list, `frappe.views.calendar[doctype]` for the
calendar, and `frappe.treeview_settings[doctype]` for the tree. The `calendars` and `treeviews`
hooks list which doctypes offer those views, and both reach the client through the boot payload.

**Guards:** All three are plain objects, keyed by doctype and read once when the view opens. An
app that assigns the whole entry drops what another app put there, and the last script evaluated
wins. The list settings are read for the indicator as well, so `get_indicator` changes how every
row of the list is coloured. Client Scripts for the List view are evaluated after the app files,
so a site can override an app's settings, which is deliberate.

## Good use

Add keys to the entry rather than assigning it.

```javascript
frappe.listview_settings["Delivery Trip"] = frappe.listview_settings["Delivery Trip"] || {};
Object.assign(frappe.listview_settings["Delivery Trip"], {
    add_fields: ["status", "driver"],
    get_indicator(doc) {
        return [__(doc.status), doc.status === "Completed" ? "green" : "orange", `status,=,${doc.status}`];
    },
});
```

Name every field the settings read in `add_fields`. The list fetches a fixed set of columns, so a
field that `get_indicator` or a formatter reads without being listed is `undefined` for every
row.

Keep the per-row work to a comparison. `get_indicator` and a list formatter run once per row on
every page of every list. A server call or a lookup there multiplies by the page length.

Sort and filter on indexed columns. A default sort or a default filter in the settings applies to
every list load of the doctype.

Declare the doctype in `calendars` or `treeviews` when the app adds that view, and put the view's
configuration in the matching registry.

## Rules

- A21 — Add to a client-side registry. Do not replace what another app put there
- A38 — Every `frappe.call` target resolves to a whitelisted method that still exists
