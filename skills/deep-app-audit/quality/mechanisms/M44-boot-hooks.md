---
id: M44
---
# M44 — Boot hooks

**What:** Several hooks add data to the payload the desk receives at session boot, or register a
source the desk queries later. `extend_bootinfo` and `boot_session` receive the `bootinfo` dict
and add keys to it. `filters_config` returns extra list filter operators. `awesomebar_search`
adds a search source to the global search bar. `notification_config` declares the counters in
the notification panel. `global_search_doctypes` seeds Global Search Settings per domain.
`use_json_request_body` opts one app into JSON request bodies. `sqlite_search` registers a
search index class.

**Guards:** `extend_bootinfo` is called with the keyword `bootinfo=`; `boot_session` is called
with one positional argument. Every handler runs on every desk boot, in app order, in the
request that serves the first page after login. `awesomebar_search` is the only one with error
isolation: a handler that raises is logged and skipped, a handler that returns a value that is
not a list or a tuple is dropped, and at most 20 items per handler are kept. A `sqlite_search`
class must subclass `SQLiteSearch`. The boot payload is serialised into the desk page, so its
size is paid by every user on every load.

## Good use

The handler adds one small, flat namespace, and it queries as little as possible.

```python
# hooks.py
extend_bootinfo = "my_app.boot.boot_session"
```

```python
# my_app/boot.py
import frappe


def boot_session(bootinfo):
	bootinfo.my_app = {
		"routing_enabled": frappe.db.get_single_value("My App Settings", "routing_enabled"),
	}
```

The handler writes under a key named after the app. It does not write a list of documents, a
count over a large table, or a value that only one screen reads. Data one screen needs is
fetched by that screen.

The handler adds keys. It does not edit a value the framework or another app already put in
`bootinfo`, because the next handler and the client both read that value.

An `awesomebar_search` handler returns a list of dicts. It returns an empty list when it has no
match, and it keeps its query bounded, because the handler runs on each keystroke group in the
search bar.

## Rules

- A26 — A hook handler returns what the call site expects.
- B30 — Do not change a collection while you iterate it, and copy a shared object before you edit it.
- B40 — An optional step must not fail the main flow, and a swallowed failure must be logged.
