---
id: M10
---
# M10 — Controller class per DocType

**What:** Every standard DocType has one controller class. `import_controller` loads
`<app>/<module>/doctype/<scrubbed_name>/<scrubbed_name>.py` and takes the class whose name is
the DocType name with spaces and hyphens removed. The class holds the DocType's lifecycle
methods and its whitelisted document methods. It is the main place an app puts the business
rules of its own DocTypes.

**Guards:** The class must subclass `BaseDocument`, else the import raises. A DocType with
`custom=1` never loads a controller file: it gets `NestedSet` when `is_tree` is set, and
`Document` otherwise. `get_controller` caches the class per site, so a code change needs a
restart or a reload. `override_doctype_class` and `extend_doctype_class` are applied on top of
the imported class, in that order. `run_method` refuses any method name that starts with `_`.
A field and a method cannot share a name: `run_method` prefers the instance attribute, so a
fieldname that shadows a method makes the method uncallable.

## Good use

Put the DocType's rules in its own controller, and keep the controller about that DocType only.

```python
# my_app/my_app/doctype/haulage_note/haulage_note.py
from frappe.model.document import Document


class HaulageNote(Document):
    def validate(self):
        self.set_total_weight()

    def on_submit(self):
        self.create_trip_log()
```

Use the framework's lifecycle names exactly. A method with a name the framework does not call is
dead code that looks live.

Give a helper method a name that no field uses, and give a field a name that no method uses. The
generated type block at the top of a controller lists every fieldname, so the conflict is
visible in the same file.

Keep the class small. A rule that concerns two DocTypes belongs in a module both controllers
call, not copied into each.

Do not write a controller file for a DocType created from the UI with `custom=1`. The file is
never imported, so the rules in it never run.

Do not keep state on the class. A controller class is cached per site and shared by every
document of that DocType in the process.

## Rules

- B33 — Use a lifecycle method name the framework calls
- A30 — Do not ship code for a DocType created with `custom=1`
- A07 — Reuse the DocType the stack already models
