---
id: M23
---
# M23 — `importable_doctypes`

**What:** The `importable_doctypes` hook adds doctype names to the folder walk that
`bench migrate` runs over every module of every app. A name in the hook makes the framework
import `<module>/<scrubbed name>/<record>/<record>.json` the same way it imports the standard
importable set.

**Guards:** Each hook value is scrubbed and added to `IMPORTABLE_DOCTYPES` with no module of its
own, so the walk finds the folder in any module of any app. The hook widens the walk for every
app on the site, not for the declaring app alone. The walk order is the order of the built-in
list first, then the hook values, so a record cannot depend on a record from another folder
being imported first.

## Good use

Use the hook when the app defines a doctype whose records are code: a definition that a
developer edits in a file, keeps in version control, and reviews in a pull request. The doctype
needs a `module` field, and its records need the standard exported layout of one folder per
record with a JSON file of the same name.

Keep the set small. Every name in the hook is one more folder that the framework looks for in
every module of every installed app on every migrate.

A record that a user creates and edits on the site does not belong here. The migrate import
overwrites it from the file.

## Rules

- A24 — A `hooks.py` value is static data, computed once per process
