---
id: M58
---
# M58 — Monkeypatching

**What:** An app can replace a function, a method or an attribute of frappe, of another app, or
of a third-party package, by assigning to it at import time. This is not a mechanism the
framework offers. There is no hook that reads it, no registry that records it, and no place in
the framework that calls it.

**Guards:** Nothing guards it. The patch takes effect when the module that applies it is
imported, and that moment depends on the import graph of the process. Two apps that patch the
same name are resolved by import order, which changes between a web worker, a background
worker, a bench command and a test run. A patch applied in `hooks.py` never runs at all,
because `_load_app_hooks` drops functions, classes and modules from the hook dict. A patch has
no uninstall path: removing the app removes the patch, and any data written under its behaviour
stays. The upstream function it replaces changes with every release, and the app carries a copy
of a signature it does not own.

Frappe patches a few vendor functions itself, at a known point in the import of the framework,
and marks each one with `nosemgrep: frappe-monkey-patching-not-allowed`. Those marks record an
exception the framework owns. They are not an invitation.

## Good use

There is none. The mechanism exists as a surface an audit must look at, not as a way to
customize.

The behaviour an app wants from a patch is available through a supported mechanism in nearly
every case: `override_doctype_class` or `extend_doctype_class` for a controller,
`override_whitelisted_methods` for a whitelisted endpoint, `doc_events` for a lifecycle
reaction, a hook for a value the framework reads, and a subclass or a wrapper for the app's own
code. Where no mechanism exists, the fix is a change to the framework, so the change is
reviewed, versioned and shared.

## Rules

- A01 — Do not replace a framework or app function at import time.
- A36 — Call the framework's public surface only, and clear every deprecation warning.
- A24 — A `hooks.py` value is static data, computed once per process.
- B44 — Do not keep site or request state at module or class scope.
