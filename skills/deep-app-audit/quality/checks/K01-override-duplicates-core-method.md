---
id: K01
---
# K01 — Override methods that duplicate the core method

**Kind:** whole-surface pass over every method in the app that shadows a core method. It is not a
rule: `A02` is the rule for one override, and this check does not repeat its argument. It is not
a clone detector over the whole tree, because it looks at override methods only. It does not
cover raw-SQL coupling to core tables, and it does not cover deprecated, removed or changed
framework surface, which is `K02`.

**Why:** one override read on its own tells nothing about the app. The whole-surface view does.
It gives the count of shadowed core methods, the share of them that duplicate the core body, and
the list of core methods the app has forked without saying so. An app with one deliberate
replacement and an app that has copied a whole controller both pass a per-method review, and
only the surface-wide count separates them. The count is also the maintenance load: every
duplicated body is a core method the app must follow for the life of the app.

## Task

1. Collect the override surfaces. Parse `hooks.py` with `ast` and read the module-level
   assignments with `literal_eval`. Do not import the file, because an import runs app code. The
   surfaces are the values of `override_doctype_class` and of `extend_doctype_class`, and every
   class in the app tree whose base name resolves, through the module's own import bindings, to a
   class in another app.
2. Resolve the core class each surface shadows. The resolution follows the mechanism inventory.
   - `override_doctype_class`: `import_controller` takes the last path in the merged hook value,
     `class_overrides[doctype][-1]`, and throws `Invalid Override` when the class is not a
     subclass of the DocType's own controller
     (`frappe/model/base_document.py:import_controller`). The core class is that controller:
     the class in `<app>/<module>/doctype/<scrubbed name>/<scrubbed name>.py` whose name is the
     DocType name with spaces and hyphens removed.
   - `extend_doctype_class`: `_get_extended_class` builds a type named `Extended<Name>` whose
     bases are the extension classes in reverse hook order, followed by the controller. An
     extension is not required to subclass anything, so the core class is the first class in that
     method resolution order that carries the method: another app's extension, else the
     controller.
   - A controller subclass: the core class is the base class named in the class statement,
     resolved through the import bindings of the module that holds it.
   - A DocType with `custom: 1` has no controller file, so an override registered for it shadows
     `Document` or `NestedSet` only.
3. List the methods of each override class, and keep the methods whose name the resolved core
   class also carries. A method that the core class does not carry adds behaviour and leaves the
   check.
4. Record for each kept method whether the body holds a call to `super().<same name>()`.
5. Measure the duplication. Take the body of both methods, drop the docstring, unparse each
   statement, and strip the layout. Compare the two line sequences and record the share of the
   override body that the core body also holds, with the length of both bodies.
6. Read the core method at each site and give the verdict. A method with no `super()` call and a
   high duplication share is a copy of the core body: every later core change to that method is
   lost for the site, and nothing says so. A method with no `super()` call and a low share
   replaces the core step on purpose; the finding is then whether the core body does work that
   the replacement drops. A method that calls `super()` and still repeats core lines runs the
   core step twice.
7. Rank by the duplication share, then by the length of the core body. A duplicated body of 40
   lines carries more lost core changes than a duplicated body of 3.

Server Scripts, Client Scripts and Property Setters live in the site database, and this check
reads the app tree and its git history only. An override written as a Server Script is out of
reach, unless the app ships it as a fixture file.

## Inputs

- The app tree, with its `hooks.py` and its Python modules.
- A checkout of `frappe` and of every app the target names in `required_apps` or imports, at the
  bench revision of `develop`. The comparison is against the core method as it stands there.
- The mechanism inventory, for the resolution order of step 2.

## Output

| Column | Content |
|---|---|
| Surface | `override_doctype_class`, `extend_doctype_class`, or `controller subclass` |
| DocType | The DocType the override is registered for. Empty for a controller subclass |
| App method | App file, class and method name |
| Core method | Core app, file, class and method name |
| Calls super | Whether the body calls `super().<same name>()` |
| Duplication | Share of the override body that the core body also holds |
| Body size | Length of the override body and of the core body, in statements |
| Verdict | `duplicate`, `partial duplicate`, `replacement`, or `duplicate with super` |

A second table holds one row per override class, with the count of shadowed core methods, the
count with a `duplicate` verdict, and the share of the class's methods that shadow core. That
table separates a thin override from a copied controller.
