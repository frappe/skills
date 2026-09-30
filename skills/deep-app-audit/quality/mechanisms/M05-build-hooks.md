---
id: M05
---
# M05 — Build hooks

**What:** `bench build` runs `after_build` for each app it built, and `after_app_build` for
every app on the bench. `after_app_build` receives the list of apps that were built. Both hooks
exist so an app can post-process its own built assets, for example to write a manifest or to
copy a generated file into `public`.

**Guards:** The hooks run from a bench command, not from a request. `bench build` resolves the
method with a plain `import_module`, not with `frappe.get_attr`, so the path must import without
a site. There is no site context and no database connection. `after_build` runs only for the
apps in the build; `after_app_build` runs for every app, so a handler must read the argument and
return early for a build it does not care about.

## Good use

Treat a build hook as a file-system step in a build pipeline. It reads and writes files under
the app directory, and nothing else.

```python
# my_app/build.py
def after_build():
    _write_icon_manifest()
```

Write `after_app_build` with one parameter and use it to decide whether to run.

```python
# my_app/build.py
def after_app_build(apps):
    if "my_app" not in apps:
        return
    _write_icon_manifest()
```

Do not read or write the database, do not call `frappe.get_doc`, and do not read site config. A
build runs on a bench that may have no site, and `bench build` is also run in CI images where no
site exists.

Keep the hook fast and deterministic. Every developer on the bench pays its cost on every build.

## Rules

No rule in the knowledge base covers this mechanism yet.
