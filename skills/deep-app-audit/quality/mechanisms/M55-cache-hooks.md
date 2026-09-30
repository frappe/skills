---
id: M55
---
# M55 — Cache hooks

**What:** `persistent_cache_keys` names key patterns that survive a full cache clear.
`clear_cache` names functions that run after a full cache clear, so an app can drop its own
cached values.

**Guards:** Both hooks are read in the "everything" branch of `frappe.clear_cache()` only. A
clear scoped to a DocType or to a user runs neither. The full clear collects every key of the
site, removes the keys that match each `persistent_cache_keys` pattern, and deletes the rest;
the `clear_cache` functions then run. A pattern is matched as a key prefix, so a short pattern
keeps more than the app expects. A key kept this way survives `bench clear-cache` and a
migrate, so anything that must change with the code must not be listed.

## Good use

The app names its own keys with a prefix that no other app uses, and lists only the keys whose
content is not derived from code or schema.

```python
# hooks.py
persistent_cache_keys = ["my_app||rate_limit||"]
clear_cache = "my_app.cache.clear"
```

```python
# my_app/cache.py
import frappe


def clear():
	frappe.cache.delete_keys("my_app||permit_index||")
```

A rate limit counter or a lockout counter is a good candidate to keep: clearing it hands the
caller a fresh allowance. A cached document, a cached meta value, a cached template or a cached
route map is not: those are derived from code and schema, and a migrate must invalidate them.

An app that needs a cached value with an owner and an invalidation rule uses the framework
cache decorators instead of a raw key, because they carry the site prefix and the scope.

## Rules

- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve.
- B44 — Do not keep site or request state at module or class scope.
