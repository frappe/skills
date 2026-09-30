---
id: A26
area: customization
mechanism: M31
---
# A26 — A hook handler returns what the call site expects

**Why:** Several hooks feed their return value straight back into the framework. A handler that
returns `None` replaces a document with nothing, or a dashboard with nothing. The failure is an
`AttributeError` deep inside core, on a path the app never touched.

## Bad

```python
# my_app/hooks.py
after_file_upload = "my_app.files.stamp"
override_doctype_dashboards = {"Item": "my_app.dashboards.item"}
```

```python
# my_app/files.py
def stamp(doc):
	doc.custom_source = "portal"  # returns None
```

```python
# my_app/dashboards.py
def item(data=None):
	data["transactions"].append({"label": "Permits", "items": ["Permit"]})  # returns None
```

## Good

```python
# my_app/files.py
def stamp(doc):
	doc.custom_source = "portal"
	return doc
```

```python
# my_app/dashboards.py
def item(data=None):
	data = data or {}
	data.setdefault("transactions", []).append({"label": "Permits", "items": ["Permit"]})
	return data
```

## Find

- For every hook in `hooks.py`, check the handler for a `return` statement on every path.
- `rg -n 'after_file_upload|override_doctype_dashboards|update_website_context|get_print_format_template|pdf_body_html|pdf_generator|additional_timeline_content|awesomebar_search' hooks.py`.
- A handler for one of those hooks whose body ends without a `return`.

## Confirm

`uploadfile` reassigns `doc` from every `after_file_upload` hook and then calls `doc.save()`
(`frappe/handler.py`). A handler that returns nothing breaks every upload.

`get_dashboard_data` wraps the hook result in `frappe._dict(...)`
(`frappe/model/meta.py:get_dashboard_data`). A `None` return raises there. The hook is skipped
entirely when `meta.custom` is set, so a dashboard hook for a Custom DocType never runs.

`Document.hook` collates dict returns from lifecycle handlers and drops every other type
(`frappe/model/document.py:hook`). A `doc_events` handler that returns a list or a string is not a
finding, but the value is lost. Returning a value from a `doc_events` handler is nearly always a
mistake.

`additional_timeline_content` must return a list. `awesomebar_search` errors are logged and
skipped, so a wrong return there is silent.

`pdf_generator` is a special case. See A27.
