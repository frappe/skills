---
id: B12
area: correctness
mechanism: M04
---
# B12 — Reload the DocType before a patch reads a field the same release adds

**Why:** `bench migrate` runs `pre_model_sync` patches, then syncs every DocType JSON, then
runs `post_model_sync` patches. A `pre_model_sync` patch sees the old meta and the old columns.
A patch that reads a field the same release adds fails with an unknown column and stops the
migration for the whole site.

## Bad

```python
# patches.txt: [pre_model_sync]
# my_app.patches.v1_0.set_region_code
def execute():
    frappe.db.sql("update `tabRoute` set region_code = 'IN' where region_code is null")
```

## Good

```python
# patches.txt: [post_model_sync]
# my_app.patches.v1_0.set_region_code
def execute():
    frappe.reload_doc("my_app", "doctype", "route")
    frappe.db.set_value("Route", {"region_code": ("is", "not set")}, "region_code", "IN")
```

## Find

- Read `patches.txt` in the app. Every patch under `[pre_model_sync]` is a candidate.
- `rg -n 'frappe\.reload_doc|reload_doctype' patches/`. A patch that reads a new field and has
  neither is a candidate.
- Compare the fields a patch reads with the fields added to the DocType JSON in the same
  release.
- `rg -n 'frappe\.get_meta\(|frappe\.get_doc\("DocType"' patches/` in a `pre_model_sync` patch.
  Both return the old definition there.

## Confirm

A `pre_model_sync` patch is correct when it must read data in its old shape, for example before
a field is renamed or a fieldtype changes. Everything else belongs in `post_model_sync`. Very
few patches need the old schema.

Develop also has a `[post_fixture_sync]` section that runs after fixtures
(`source:frappe/modules/patch_handler.py:PatchType`). The public migration guides do not
mention it, and the two guides disagree with each other about which meta a
`pre_model_sync` patch sees; `frappe/migrate.py` settles it, because it runs
`pre_model_sync` before `sync_all`.
