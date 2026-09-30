---
id: M41
---
# M41 — Field and link formatters

**What:** `frappe.form.formatters` maps a fieldtype to a function that renders a value in a
form, a grid and a list. `frappe.form.link_formatters` maps a DocType to a function that
renders the label of a link to that DocType. Both are plain JavaScript objects, loaded from a
desk bundle.

**Guards:** Both objects are plain. An assignment to a key replaces what the previous script
put there, and the last bundle loaded wins. The Link formatter applies
`link_formatters[doctype]` only when the linked DocType is not the DocType of the document on
screen, so a self link keeps the raw name. A formatter runs once per rendered cell, so its cost
is multiplied by the number of rows on the page.

## Good use

An app adds a key for a DocType it owns, and leaves every other key alone.

```javascript
// my_app/public/js/permit_formatter.js
frappe.form.link_formatters["Permit"] = (value, doc, docfield) => {
	if (!value) return "";
	return doc && doc.permit_title ? `${value}: ${doc.permit_title}` : value;
};
```

The formatter receives the value, the document that holds the field, and the docfield. It
returns HTML. It reads values that are already in the document. It makes no server call,
because it runs for every cell in a list of a hundred rows.

A change that belongs to one field, not to a whole fieldtype, goes in the docfield instead.
`formatters._apply_custom_formatter` calls `df.formatter` when the docfield carries one, so a
form script can format one field without touching the shared registry.

A new fieldtype the app defines takes a new key. A core fieldtype such as `Currency`, `Link` or
`Date` is rendered for every DocType on the site, so a replacement of that key changes every
form and every list, including the ones other apps own.

## Rules

- A21 — Add to a client-side registry. Do not replace what another app put there.
