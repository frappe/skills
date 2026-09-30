---
id: M01
---
# M01 — `hooks.py` loading and merge

**What:** `hooks.py` is the declaration file of an app. Every mechanism in this knowledge base
that is not a controller method or a database record is declared there. `_load_app_hooks`
imports `<app>.hooks` for each active app and keeps every public module-level name that is not
a module, a function, or a class. `append_hook` turns a scalar into a one-item list and merges
a dict key by key, so the merged value of a hook is a list, or a dict of lists.

**Guards:** `_is_valid_hook` drops a callable, so a function object in `hooks.py` disappears
without a message. App order in `apps.txt` decides list order: a "last wins" hook reads `[-1]`
and a "first wins" hook reads `[0]`. Outside developer mode the merged dict is cached in the
client cache under `app_hooks`, so an edit to `hooks.py` has no effect until a cache clear or a
migrate. `frappe.get_attr` raises `AppNotInstalledError` when the first segment of a dotted path
is not an installed app.

## Good use

A hook value is data. Write a literal string, list, or dict, and let the framework resolve the
dotted path when it needs the code.

```python
# my_app/hooks.py
app_name = "my_app"

doc_events = {
    "Sales Invoice": {
        "on_submit": "my_app.sales.invoice.on_submit",
    }
}
```

Give the module no work to do at import time. `hooks.py` is imported before a site is chosen,
so a database read, a settings read, or a `frappe.local` read at module level either fails or
freezes one site's answer for the whole process.

Read one app's own hooks with `frappe.get_hooks(app_name="my_app")`. This skips the merge and
returns only that app's values, which is what install code and migrate code need.

Use `frappe.get_hooks("hook_name")` for the merged view. The result is always a list, so a
handler that expects one value reads `[-1]` or `[0]` and matches the mechanism the framework
uses for that hook.

The `Audit System Hooks` report shows the merged view per app on a live site. Use it to see
which app supplies which value before you change the order of `apps.txt`.

After any change to `hooks.py`, run `bench clear-cache` on the site. A developer that skips this
step tests the old value.

## Rules

- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve
- A24 — A `hooks.py` value is static data, computed once per process
- A13 — Every module the app imports at load must be declared and present
- A27 — A handler for a last-wins hook must yield to the apps it does not own
