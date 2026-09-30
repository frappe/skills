---
id: M33
---
# M33 — Link field search

**What:** A link field asks the server for its options through `search_link`. Three mechanisms
change what it returns: the `standard_queries` hook replaces the default search for a doctype,
`frm.set_query` on the client sends filters or the path of a query function for one field, and
`validate_and_sanitize_search_inputs` wraps a query function.

**Guards:** A `standard_queries` entry is read as `[-1]`, so the last app in the list wins for
that doctype, and it is used only when the client sends no `query` of its own. The query path must
resolve and must be whitelisted, or the request answers with a "Method not found" page outside
developer mode. The framework calls the function with the doctype, the search text, the search
field, the start, the page length and the filters as positional arguments, and with `as_dict`,
`reference_doctype`, `ignore_user_permissions` and `link_fieldname` as keyword arguments. The call
goes through `frappe.call`. A function with fewer than six positional parameters raises on every
keystroke.

## Good use

Prefer `set_query` with filters. It needs no server code, it is read where the field is, and it
composes with the framework's own search, its permissions and its user permissions.

```javascript
frm.set_query("driver", () => ({ filters: { status: "Active", branch: frm.doc.branch } }));
```

Write a query function when the options depend on something a filter cannot express, such as a
join or a computed set. Whitelist it, wrap it with `validate_and_sanitize_search_inputs`, and
keep the full signature that the call site passes.

```python
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def driver_query(doctype, txt, searchfield, start, page_len, filters, **kwargs):
    ...
```

Use `standard_queries` only for a doctype the app owns, and only when every link to it needs the
same search. The hook takes the doctype for the whole site, and the last installed app wins, so
two apps that claim one doctype leave one search.

Keep the query fast and bounded. It runs on every keystroke in the field. Filter on indexed
columns, honour `start` and `page_len`, and return the columns the field displays and no more.

## Rules

- A25 — A hook handler accepts every argument the call site passes
- A27 — A handler for a last-wins hook must yield to the apps it does not own
