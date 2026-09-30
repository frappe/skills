---
id: M37
---
# M37 — Desk files for the app's own doctype

**What:** The desk loads code for a doctype from the doctype folder, by file name.
`<doctype>.js` and `<doctype>.css` serve the form, `<doctype>_list.js` the list,
`<doctype>_calendar.js` the calendar, `<doctype>_tree.js` the tree, `<doctype>_list.html` the
list row template, and `regional/<country>.js` and `regional/<country>_list.js` the country the
site is set to. Any `.html` file in the folder becomes a client template, and
`form_grid_templates` in the controller module maps a fieldname to a grid row template.

**Guards:** None of this is loaded when the doctype is custom. The country files are loaded only
when System Settings names a country, and they are appended after the main file, so they add to
it and do not replace it. After these files, the framework appends the files that other apps
registered through `doctype_js` and its siblings, and after those the site's Client Scripts. The
whole set is concatenated into one string per asset and evaluated as one function, so a syntax
error in one file breaks every file in that asset.

## Good use

These files belong to the app that owns the doctype, in the doctype folder, next to the
controller. They are the app's own UI and they are the right place for the form behaviour the
app always needs.

Keep them to the view. What the file does is set queries, toggle display, add buttons and format
what the user sees. A rule that must hold lives in the controller, because the desk is one writer
among many.

Use a regional file for a country-specific field or label on a doctype the app owns. The regional
file runs after the main file, so it changes the form the main file already set up.

An app that must add behaviour to a doctype it does not own does not put a file in that doctype's
folder. It registers its own file through `doctype_js`.

A doctype created in the desk with `custom=1` loads none of these files. Give it a Client Script,
or make the doctype a standard doctype in the app.

## Rules

- A21 — Add to a client-side registry. Do not replace what another app put there
- A30 — Do not ship code for a DocType created with `custom=1`
- A38 — Every `frappe.call` target resolves to a whitelisted method that still exists
- B45 — Refresh the field after code changes `frm.doc`
