---
id: M56
---
# M56 — File hooks

**What:** `after_file_upload` post-processes the File document that an upload created, before it
is saved. `before_write_file` is called with the file size before the bytes are written.
`write_file` replaces the storage backend. `write_file_keys` lists the fields copied from an
existing File row when a new upload has the same content hash. `ignore_file_permissions` turns
off the File permission check.

**Guards:** `after_file_upload` feeds its return value back: the upload handler reassigns `doc`
from each handler in turn and then calls `doc.save()`, so a handler that returns nothing breaks
every upload with an `AttributeError` inside core. Handlers run in app order and each one
receives what the previous one returned. `before_write_file` runs on both write paths, before
any bytes are stored, and it receives the size only, so it can reject a file but cannot inspect
it. `ignore_file_permissions` is read with `any()`, so one app that declares it removes the
check for the whole bench.

## Good use

An `after_file_upload` handler edits the document and returns it.

```python
# hooks.py
after_file_upload = "my_app.files.tag_source"
```

```python
# my_app/files.py
def tag_source(doc):
	doc.custom_source = "portal"
	return doc
```

The handler returns the document on every path, including the paths where it decides to change
nothing.

A `before_write_file` handler enforces a limit and throws with a message that names the limit:

```python
# my_app/files.py
import frappe
from frappe import _


def check_size(file_size):
	limit = frappe.get_cached_value("My App Settings", "My App Settings", "max_upload_mb")
	if limit and file_size > limit * 1024 * 1024:
		frappe.throw(_("File is larger than the limit of {0} MB").format(limit))
```

Both handlers run inside the upload request. Work that takes time, such as a virus scan, an
image conversion or an upload to an external store, is enqueued and not done inline.

## Rules

- A26 — A hook handler returns what the call site expects.
- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve.
