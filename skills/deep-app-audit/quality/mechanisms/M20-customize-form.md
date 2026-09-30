---
id: M20
---
# M20 — Customize Form

**What:** Customize Form is the desk tool that writes Custom Fields (M18) and Property Setters
(M19) for one DocType. It shows the current meta, lets a user change field properties, and
saves the difference as records. It is the mechanism a site owner uses; an app uses M18 and M19
directly.

**Guards:** `validate_doctype` refuses a DocType in `core_doctypes_list`, a Single DocType, and
a DocType with `custom=1`. `allow_property_change` refuses, with a message and no error, the
changes that break core assumptions: enabling `allow_on_submit` on a standard field, unsetting
`reqd` on a standard field, unsetting `read_only` on a standard field, setting `options` on a
fieldtype outside `ALLOWED_OPTIONS_CHANGE`, setting `translatable` on a fieldtype that does not
support it, marking a standard field `is_virtual`, and putting a fieldtype into "In List View"
that cannot be shown there. A fieldtype change must stay inside a group of
`ALLOWED_FIELDTYPE_CHANGE`, and a length reduction is checked against the data already stored.

## Good use

Customize Form is the right tool for a site: a label change, a field order change, a default
value, a naming series, a field the site added for itself. The refusals are the framework
telling the user that core depends on the property they are changing, so treat a message from
Customize Form as a rule, not as an obstacle to work around.

An app must not depend on a Customize Form change. The tool is driven by a user, and its output
is Custom Field and Property Setter records that no app owns. When the app's code reads a field,
the app creates that field in install code. When the app's behaviour needs a property change,
the app writes the Property Setter in install code, with `module` set, and removes it on
uninstall.

An app also cannot use Customize Form for a core DocType, a Single DocType, or a custom DocType.
For a Single DocType the app changes the JSON it owns, or writes a Property Setter directly. For
a DocType another app owns and that Customize Form refuses, ask whether the change is safe at
all before writing the record by hand: the same refusal that Customize Form gives applies to the
site, and writing the Property Setter directly only removes the warning.

Export what the site customized with the `custom/` folder sync or as a documented setup step, so
a second site gets the same result. A change made once in the desk on one site exists on that
site only.

## Rules

- A17 — Do not unset `reqd` or `read_only` on a standard field
- A18 — Before you make a standard field mandatory or hidden, find every writer
- A08 — Create the Custom Fields the app's logic reads in code, not as fixtures
- A10 — Remove the app's Custom Fields and Property Setters on uninstall
