---
id: M26
---
# M26 — DocType Layout

**What:** A DocType Layout record gives one doctype a second form: its own field order, its own
child tables, a display condition, a default print format, a default email template, and its own
client script. The desk opens the layout by its own route.

**Guards:** The layout's client script is appended to the standard doctype JavaScript and runs
with it. While a layout is active, the form Client Scripts of the doctype are skipped, so every
Client Script behaviour has to be repeated in the layout script. List Client Scripts are not
affected, because the list view is not opened through the layout.

## Good use

A layout suits a doctype that serves more than one kind of work: one layout per role, per
process, or per document variant, over one table and one controller. The data model does not
change, so reports, permissions and the API see one doctype.

Put the layout's JavaScript in its own client script field, next to the field list it belongs
to. The script runs for the layout only, which is what makes a layout self-contained.

Check the doctype for Client Scripts before you introduce a layout on a live site. Every form
Client Script on the doctype stops running the moment a user opens the layout, and nothing warns
about it. Move that code into the layout script first.

Server-side rules are unaffected by a layout, so a validation stays in the controller and holds
for every layout.

## Rules

- A20 — A rule that must always hold does not live in a Client Script
- B45 — Refresh the field after code changes `frm.doc`
