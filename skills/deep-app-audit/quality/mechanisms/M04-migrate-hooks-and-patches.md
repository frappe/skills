---
id: M04
---
# M04 — Migrate hooks and `patches.txt`

**What:** `bench migrate` runs `before_migrate` for each installed app, then the
`pre_model_sync` patches, then the DocType sync, then the `post_model_sync` patches, then
fixtures and the `post_fixture_sync` patches, and last `after_migrate`. `patches.txt` lists the
patches of one app in three sections. A patch is a module with an `execute()` function.

**Guards:** `run_all` reads the `Patch Log` and skips every patch string that is already there,
so a patch runs once per site under the name it was listed with. A line prefixed with `finally:`
runs after every other patch. `frappe.flags.in_patch` and `frappe.flags.in_migrate` mute
Notifications, Webhooks, and Server Scripts, so a data change made by a patch fires no
data-driven event. A Property Setter saved under `in_patch` also skips
`validate_fields_for_doctype`.

## Good use

Use `before_migrate` and `after_migrate` for work that must run on every migrate, such as
clearing an app cache the app itself built. Use a patch for a one-time data change.

Put a patch in the section that matches what it reads.

- `pre_model_sync`: the patch reads the schema as it is in the running release. Use it when the
  new DocType JSON would break the read, for example when a field is about to be removed.
- `post_model_sync`: the patch needs the new schema. This is the usual section.
- `post_fixture_sync`: the patch needs a record that a fixture supplies.

A `post_model_sync` patch still runs before the DocType it reads is reloaded in some paths, so
call `frappe.reload_doc` or `frappe.reload_doctype` at the top of a patch that reads a field the
same release adds.

```python
# my_app/patches/v1_0/set_region_code.py
import frappe


def execute():
    frappe.reload_doctype("Delivery Note")
    frappe.db.sql(
        """update `tabDelivery Note` set region_code = 'DEFAULT'
           where region_code is null or region_code = ''"""
    )
```

Write every patch so that a second run changes nothing. A migrate that fails halfway leaves the
site part-migrated, and the operator runs `bench migrate` again. A patch that appends, that
increments, or that inserts without a guard doubles its effect.

Keep a patch bounded. A patch that loads every row of a large table into memory times out on a
big site and never reaches its own `Patch Log` row, so the next run starts again from nothing.
Process in batches and commit per batch.

Do not remove a line from `patches.txt` when you rename the module. The string in the file is
the key in `Patch Log`. A rename makes the patch run again on every existing site. When a
rename is needed, add the new line and leave the old one.

## Rules

- A23 — Install, migrate, and patch code cannot rely on Notifications, Webhooks, or Server Scripts
- B11 — A patch must produce the same result when it runs twice
- B12 — Reload the DocType before a patch reads a field the same release adds
- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve
- B03 — Keep schema statements out of a transaction that holds writes
- B13 — Ship a data patch with a schema change that existing rows cannot satisfy
