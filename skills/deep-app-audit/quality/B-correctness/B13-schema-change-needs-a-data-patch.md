---
id: B13
area: correctness
---
# B13 — Ship a data patch with a schema change that existing rows cannot satisfy

**Why:** A DocType JSON change applies to every site at the next migrate. Existing rows keep
the values they have. A new mandatory field, a new unique constraint, or a changed fieldtype
makes those rows invalid. The site then fails the migration, or fails at the next save of a row
nobody has touched for years.

## Bad

```json
// my_app/my_app/doctype/route/route.json, no patch shipped
{ "fieldname": "region_code", "fieldtype": "Data", "reqd": 1, "unique": 1 }
```

## Good

```python
# my_app/patches/v1_0/backfill_region_code.py, listed in [post_model_sync]
# The field ships with reqd: 0 and unique: 0 in this release. A later release turns them on.
def execute():
    frappe.reload_doc("my_app", "doctype", "route")
    rows = frappe.get_all("Route", filters={"region_code": ("is", "not set")}, pluck="name")
    for name in rows:
        frappe.db.set_value("Route", name, "region_code", derive_region_code(name))
```

## Find

- `git -C <app> diff <last release>..HEAD -- '*/doctype/*/*.json'` for added `"reqd": 1`,
  added `"unique": 1`, a changed `"fieldtype"`, a changed `"precision"`, or a removed field.
- For each such change, look for a matching file under `patches/` and a line in `patches.txt`.
- `rg -n 'rename_field' patches/`. A renamed fieldname in a DocType JSON with no `rename_field`
  patch loses the data, because the old column stays and the new one is empty.
- A Single DocType with a new default: the default does not reach existing sites.

## Confirm

A new optional field with no default needs no patch. A widened field, such as `Data` to
`Small Text`, needs no patch. A removed field needs a patch only when other code still reads
the column; the column itself stays in the table, because the framework has no reverse schema
migration. Permissions never sync on migrate, so a permission change needs an explicit
`execute:frappe.permissions.reset_perms("<DocType>")` line.
