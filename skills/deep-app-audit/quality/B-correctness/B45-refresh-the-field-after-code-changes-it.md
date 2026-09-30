---
id: B45
area: correctness
---
# B45 — Refresh the field after code changes `frm.doc`

**Why:** The form keeps its own rendered state. A value written straight onto `frm.doc` changes
the model and not the control, so the user still sees the old value and may overwrite the new
one. A child row added without a refresh does not appear at all, and the grid loses its order
after a reorder.

**Applies to:** apps that ship form scripts, and sites that use Client Script records.

## Bad

```javascript
frappe.ui.form.on("Delivery Note", {
    customer(frm) {
        frm.doc.shipping_rule = "Standard";
        const row = frm.doc.items[0];
        row.warehouse = "Main - X";
        frm.save();
    },
});
```

## Good

```javascript
frappe.ui.form.on("Delivery Note", {
    customer(frm) {
        frm.set_value("shipping_rule", "Standard");
        frappe.model.set_value(
            frm.doc.items[0].doctype, frm.doc.items[0].name, "warehouse", "Main - X"
        );
        frm.refresh_field("items");
    },
});
```

## Find

- `rg -n 'frm\.doc\.\w+\s*=' --type js` in the app and in Client Script records.
- `rg -n 'frm\.doc\.\w+\.push\(|frm\.add_child\(' --type js` with no `frm.refresh_field` after
  it.
- `rg -n 'frm\.save\(\)' --type js` where the values above it were set on `frm.doc` directly.
  The form is not marked dirty, so the save may do nothing.
- `rg -n 'set_df_property\([^)]*"options"' --type js` on an Autocomplete or MultiSelect control.
  Those need `set_data` or `set_options`.

## Confirm

`frm.set_value` refreshes the control, marks the form dirty and fires the field's own event, so
it needs no extra call. `frappe.model.set_value` on a child row does the same for that row, but
the grid still needs `frm.refresh_field` when rows were added, removed or reordered. A read of
`frm.doc` needs nothing. A value set in `onload` before the form renders is refreshed by the
first render. Client Scripts run after the app's own form script
(`source:frappe/public/js/frappe/form/script_manager.js:ScriptManager.setup`), so an app script
that sets a value can be overwritten by a site script and the reverse is not true.
