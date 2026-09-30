---
id: M14
---
# M14 — `extend_doctype_class`

**What:** `extend_doctype_class` maps a DocType name to one or more dotted paths to classes.
`_get_extended_class` builds a new type named `Extended<Name>` whose bases are the extension
classes followed by the controller class. Every app that registers an extension for the same
DocType keeps its behaviour, which is what makes this mechanism safe where
`override_doctype_class` is not.

**Guards:** The extension list is reversed before the bases are built, so the last app in the
merged hook list ends up first in the method resolution order. A path that does not resolve
raises `ImportError` naming the path. The generated class is cached by its tuple of bases and
carries a `__reduce__` so instances can be pickled. An extension is not required to subclass the
controller, so the MRO decides which method wins, and Python raises at class creation when the
bases cannot be linearized.

## Good use

Use an extension for behaviour the app adds to a DocType it does not own.

```python
# my_app/hooks.py
extend_doctype_class = {"Sales Invoice": "my_app.extensions.sales_invoice.PermitMixin"}
```

```python
# my_app/extensions/sales_invoice.py
class PermitMixin:
    def validate(self):
        super().validate()
        self.validate_permit_number()

    def permit_is_valid(self) -> bool:
        return bool(self.get("my_app_permit_no"))
```

Write the extension as a mixin: no base class of its own, and `super()` in every method it
overrides. The extension sits before the controller in the MRO, so `super()` reaches the
controller and every other app's extension. A method that does not call `super()` cuts every app
below it out of the chain.

Prefer adding a new method to overriding an existing one. A new method has no ordering question
at all.

Do not depend on which app's extension runs first. Two apps that both extend `validate` run in
app order, and the site owner decides that order. Write each extension so that the result is the
same whichever runs first.

Do not hold state on the mixin at class level. The generated class is cached and shared.

## Rules

- A03 — Use `extend_doctype_class` when the app only adds behaviour
- A02 — An overriding controller subclasses the original and calls `super()`
- B32 — A handler must not depend on the run order of another handler
