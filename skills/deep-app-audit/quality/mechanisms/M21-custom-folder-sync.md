---
id: M21
---
# M21 — `custom/` folder sync

**What:** An app ships Custom Fields, Property Setters, DocType Links and Custom DocPerms for
one doctype as a JSON file in `<app>/<module>/custom/<doctype>.json`. `sync_customizations`
reads every such file on install, and on migrate it reads only the files whose
`sync_on_migrate` flag is set.

**Guards:** The sync path writes below the validation layer. A new Custom Field is written with
`db_insert`, and an existing one is updated with `ignore_validate`, so `check_fieldname_conflicts`
and the fieldtype change check do not run. A Property Setter is inserted with
`validate_fields_for_doctype` turned off, so the `allow_property_change` refusals that Customize
Form applies in the desk do not apply here. Every Custom DocPerm row of the doctype is deleted
and then re-inserted from the file, so permission rows that the site added are lost.
`validate_fields_for_doctype` and `updatedb` run once, after the whole file is applied. A file
for a doctype that does not exist is skipped with a printed message.

## Good use

The file is a build product, not a hand-written file. A developer customizes the doctype in the
desk, then exports the result with `export_customizations`, which needs developer mode. The
export writes the `sync_on_migrate` flag, the Custom Fields and Property Setters of the module,
the DocType Links, and one file per child table of the doctype. An export that passes through
Customize Form has already met the Customize Form guards, so the file that reaches the sync path
holds only changes that the desk accepts.

One app owns the `custom/` file for one doctype. The file describes the whole customization of
that doctype for the module, so a second app that exports the same doctype writes a second file
with the same content, and the two files fight on every migrate. An app that only needs to add
fields at install time creates them with `create_custom_fields` in an install or migrate hook
instead.

Set `sync_on_migrate` when the app must keep the customization in step with its code. Leave it
off when the file is a seed that the site is free to change afterwards.

Export permissions only when the app owns the permission model of the doctype. The sync deletes
the doctype's Custom DocPerm rows before it inserts the rows from the file. A site that set its
own permissions on the doctype loses them at the next migrate.

Every field in the file keeps a name that no other app can choose, because the sync path does
not check for a conflict. A duplicate fieldname reaches the schema step and fails the migrate
for the whole site.

## Rules

- A08 — Create the Custom Fields the app's logic reads in code, not as fixtures
- A10 — Remove the app's Custom Fields and Property Setters on uninstall
- A16 — Give every Custom Field a name that no other app can choose
- A17 — Do not unset `reqd` or `read_only` on a standard field
- A18 — Before you make a standard field mandatory or hidden, find every writer
- A19 — Keep the added columns inside the database row size limit
