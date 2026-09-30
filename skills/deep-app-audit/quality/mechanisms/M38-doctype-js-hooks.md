---
id: M38
---
# M38 — `doctype_js` and its siblings

**What:** `doctype_js`, `doctype_list_js`, `doctype_tree_js` and `doctype_calendar_js` map a
doctype to one file, or a list of files, that the app ships. The framework appends them to the
doctype's own assets, so an app can extend the form or the list of a doctype another app owns.
`page_js`, `webform_include_js` and `webform_include_css` use the same loader for pages and web
forms.

**Guards:** The files are collected by walking the active apps in order, so the load order is the
app order and an app cannot know which other app ran before it. They are appended after the
owning app's own file and before the site's Client Scripts. Each path is resolved inside the
declaring app, and a path that does not exist adds nothing and reports nothing. All the files
end up in one concatenated asset, evaluated as one function, so a syntax error in one file
breaks the doctype's whole form script.

## Good use

This is the supported way to add behaviour to another app's form. The app keeps its file in its
own folder, under a path that names the doctype it extends.

```python
# hooks.py
doctype_js = {"Sales Order": "public/js/sales_order.js"}
```

Add handlers with `frappe.ui.form.on`. Handlers accumulate, so the app's handler runs after the
owning app's handler for the same event, and both run. Do not use `frappe.ui.form.off`: it
removes every handler for that event, including the ones the owning app needs.

Do not depend on load order. Another app can register a handler for the same event, and the order
follows the install order of the site. Write a handler that produces the same result whichever
handler ran first, and read the document rather than what another handler put on the form.

Add to the client registries instead of assigning them. `frappe.listview_settings[doctype]` and
`frappe.form.formatters` are plain objects, so an assignment drops what another app placed there.

## Rules

- A21 — Add to a client-side registry. Do not replace what another app put there
- A38 — Every `frappe.call` target resolves to a whitelisted method that still exists
- B45 — Refresh the field after code changes `frm.doc`
