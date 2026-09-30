# Framework guards

This file lists what the Frappe framework already checks, and the false positive that each check
causes when a finder does not know it. Read it after `_conventions.md`, before your scope. A
verifier reads it too.

Most of what a pattern search finds in a Frappe app is guarded one frame down, by the framework,
not by the code you read. A confident finding that the framework already guards costs the
maintainer a day and costs the audit its credibility.

Each section ends with **Refute by**: the test that settles a candidate. Before you report a
candidate, find the section that covers its sink and do that test.

Everything here is framework behaviour, so it applies to any app. The file and function names are
from Frappe `develop` in 2026. Lines and defaults change between versions. When a verdict depends
on one of these rules, read the code in the framework checkout on the bench, and cite what you
read. A rule from this file is a hypothesis. A line that you read is evidence.

## 1. The document layer checks permissions

`Document` methods call `check_permission()` themselves. An endpoint with no visible check, whose
only write goes through one of them, **is guarded**.

| Call | Check | Where |
|---|---|---|
| `doc.insert()` | `create` | `Document.insert` |
| `doc.save()` on an existing document | `write` | `Document._save` |
| draft to submitted, or `update_after_submit` | `submit` | `Document.check_docstatus_transition` |
| submitted to cancelled | `cancel` | `Document.check_docstatus_transition` |
| `doc.delete()`, `frappe.delete_doc()` | `delete` | `check_permission_and_not_submitted` in `frappe/model/delete_doc.py` |
| `frappe.get_doc(dt, name, check_permission=True)` | `read` | `frappe.get_doc` |
| `get_mapped_doc(...)` | `read` on the source and `create` on the target | `frappe/model/mapper.py` |

A plain `frappe.get_doc(dt, name)` checks nothing. It only loads the document.

**The writes that bypass this layer** are the real gaps: `frappe.db.set_value`,
`frappe.db.set_single_value`, `doc.db_set`, `doc.db_update`, `frappe.db.delete`,
`frappe.db.truncate`, raw DML through `frappe.db.sql`, and any call with `ignore_permissions=True`
or after `doc.flags.ignore_permissions = True`. `Document.has_permission` returns `True` at once
when that flag is set. `get_mapped_doc` also takes `ignore_permissions`.

**Refute by:** naming each write on the path. When each one is a document-layer call with no
`ignore_permissions`, reject.

### 1a. A check that runs does not always cover

The question is not "does a check run?" It is "is each document that the endpoint puts at risk
covered by a check?" Read the source and the target separately.

The dangerous shape: the endpoint reads document A to build and insert document B. The framework
checks `create` on B, and nothing checks `read` on A. A caller who can create the cheap doctype
reads the sensitive one through it. `get_mapped_doc` checks both, so this shape occurs when the
code copies values by hand.

**Refute by:** listing each document that the endpoint touches and the check that covers it. When
the document read and the document written are the same, and the write goes through the document
layer, reject. When they are different documents, it is a candidate even though a check ran.

## 2. Reachability is part of the finding

### 2a. A controller method is reachable only through the document

`@frappe.whitelist()` on a method of a DocType controller does not make a URL for the method. The
routes to it are:

- `/api/method/run_doc_method` (`frappe/handler.py`). It loads the document with
  `check_permission=True`, so it checks **`read`**.
- `/api/v2/document/<doctype>/<name>/method/<method>` (`frappe/api/v2.py`, `execute_doc_method`),
  where the framework has it. It checks `read` for GET and **`write`** for POST.

The consequences point in two directions:

- On a doctype where no role has `read` at permlevel 0, only Administrator can load the document.
  Nobody else reaches the method, so there is no finding. Maintenance doctypes that only
  Administrator can read often have methods that start with a raw `frappe.db.delete`. A scanner
  flags them, and they are not reachable.
- `run_doc_method` checks only `read`. A method that writes through a call that bypasses the
  document layer is unguarded for each role that has `read` but not `write`. That is a real
  finding class (scope `A14`), not a non-finding.

A call to the dotted path of a controller method returns an error. It is not a second route.

**Refute by:** reading the `permissions` array of the owning doctype. No role other than
Administrator has `read`: reject. A role has `read` and not `write`: a write that bypasses the
document layer is a candidate.

### 2b. A dotted path in `frappe.enqueue` is not an endpoint

`frappe.enqueue("app.module.run_job")` makes `run_job` the target of a background job, not a
route. It is reachable over HTTP only when `@frappe.whitelist()` is on that function.

**Refute by:** finding the decorator on that function, not in its module.

### 2c. Callers do not decide reachability

- A whitelisted function with no callers in the code is still callable over HTTP by its dotted
  path. "No callers" never makes it unreachable.
- A grep hit on a function name is not proof that a form or a user can start it. A
  `frappe.ui.form.on("<DocType>")` block, a shared controller mixin, and a shared JS helper each
  make a grep give the wrong owner to a call.

**Refute by:** the decorator and the route, for reachability. For who starts it: the function
that contains the call, and its callers, not the file that grep found.

## 3. Which reads apply permissions

| Call | Applies permissions? |
|---|---|
| `frappe.get_list(...)` | yes. Its docstring says "Will also check for permissions" |
| `frappe.get_all(...)` | **no**. Its docstring says "Will **not** check for permissions" |
| `frappe.db.get_value`, `get_values`, `get_all`, `get_list`, `exists`, `count`, `sql` | **no**. The database layer checks nothing |
| `frappe.qb.get_query(...)` | **no**, by default: `ignore_permissions: bool = True` |
| `frappe.qb.get_query(..., ignore_permissions=False)` | yes, on **`select`** (or `read`), not on `read` alone |
| a query built from `frappe.qb.DocType(...)` and `.run()` | **no** |
| `frappe.client.get_list`, `/api/resource/<DocType>` | yes. These are the permissioned routes that a caller already has |

Two errors come from this table, one in each direction:

- **A port from `frappe.db.sql` to the query builder is not an authorization fix.** The query
  builder applies no permission unless the call site passes `ignore_permissions=False`. Older
  versions of `get_query` have no permission option at all.
- **`select` is not `read`.** Link and search queries check `select`. `select` without `read` is
  a deliberate grant: it lets a user pick a record in a Link field without opening it. A role gap
  computed on `read` for a link query tests a right that the endpoint does not check.

**Refute by:** naming the read call. For `get_query`, quote the `ignore_permissions` argument at
the call site. For a link or search query, compute the gap on `select`.

## 4. What `@frappe.whitelist()` validates

From Frappe 15, `@frappe.whitelist()` runs the annotations of the function through pydantic
(`transform_parameter_types` in `frappe/utils/typing_validations.py`) during a request. On an
older framework, annotations are not enforced: check that the function exists before you use this
section.

- `name: str` **is** enforced. A list or a dict raises `FrappeTypeError`, and the request gets
  HTTP 417. Do not report an operator payload against a parameter with a scalar annotation.
- `filters: dict` enforces **only the container**. The values in it can be anything.
- A parameter with **no annotation** is not validated.
- The type of the default value is added to the accepted types. `name: str = {}` accepts a dict.
  `name: str = None` accepts only a string or `None`.
- `bool` also accepts `int` and `float`.

### 4a. An operator in a dict can widen an authorized query

An endpoint takes a document name out of a `dict` parameter, or out of a parameter that is not
validated. It uses the name to decide what to authorize, then queries with the same value. Send
`{"<field>": ["like", "%"]}` in place of a name: the check authorizes the first row that matches,
and the query returns every row. The check can be correct and still not enough. The sinks that
matter are `frappe.get_doc`, `frappe.db.get_value`, `frappe.db.exists`, and
`has_permission(doc=...)`.

When a check is added without a scalar check, a list payload often fails inside
`has_permission` with an `AttributeError`, and the request gets HTTP 500. That is not a control.
It is where a type error happened to occur.

**Refute by:** reading the annotation of the parameter and the top of the module (4). A validated
scalar annotation: reject. A `dict`, a `list`, no annotation, or a string annotation, and the
value reaches one of those sinks: candidate. Also confirm that the function uses the parameter. A
search endpoint that accepts `filters` and ignores it is a false positive.

### 4b. The request shape is part of the finding

A parameter with a `dict` annotation is a dict only when the request body is JSON. A form-encoded
value is a string, and the validation rejects it with 417. A finding that needs a dict parameter
must say "JSON body", or the maintainer who reproduces it gets a 417.

## 5. `@validate_and_sanitize_search_inputs` sanitizes one parameter

The decorator (`frappe/desk/search.py`):

- sanitizes `searchfield`, and only `searchfield`
- applies `cint` to `start` and `page_len`
- returns `[]` when `doctype` does not exist

It does not sanitize `filters`, their keys or their values, and it authorizes nothing. A filter key
that becomes a column name is still an injection sink behind it. The decorator is not a guard, and
its absence is not a finding.

## 6. The DocType permission model

Read the `permissions` array in the DocType JSON. Four rules decide if a role gap is real:

1. **Only permlevel 0 decides document access.** Levels above 0 control fields. A role that
   appears only at permlevel 1 cannot open the document.
2. **Automatic roles are not a gap.** `AUTOMATIC_ROLES` in `frappe/permissions.py` is `Guest`,
   `All`, `Desk User`, and `Administrator`. Nobody grants them: `frappe.get_roles()` returns them
   for each user of the matching type. `All` includes Website Users. `Desk User` includes each
   System User. When a doctype grants `read` at permlevel 0 to one of them, each such user can
   read it by design. An endpoint that returns that data to those users crosses no boundary. When
   the grant itself is too wide for the data, that is one finding of scope `A05`, not a finding in
   each endpoint that reads the doctype.
3. **Test the right that the endpoint checks**: `select` for a link or search query (3), `read`
   for a document load, and `write`, `create`, `submit`, `cancel`, or `delete` for the document
   layer (1).
4. **A child table (`istable: 1`) has no permission rows.** The parent authorizes it. An empty
   `permissions` array on a child table does not mean "Administrator only", and a child table
   cannot be the subject of a role gap. The finding is a query that reads a child doctype without
   a check on its parent.

Also read `issingle`, `read_only`, and `is_submittable` (which adds the `submit` and `cancel`
checks of 1). A `Custom DocPerm` row on a site replaces the stock rows of its doctype, so a live
site can differ from the JSON. With a site, read the live permissions before you depend on them.

**Refute by:** quoting the permlevel 0 rows of the target doctype for the right that the endpoint
checks. When an automatic role that the actor has holds that right, or a role that the actor has
holds it, reject.

## 7. Severity: what "data they must not see" means

| What came back | Verdict |
|---|---|
| data of another party: a transaction, a balance, a price, a quantity, personal data | finding, Moderate or higher |
| configuration of a tenant: an account or category name, a period, a default setting | finding, **Low** |
| universal reference data: an exchange rate, a unit conversion factor, a country, a timezone | **not a finding** |
| a value that the roles of the actor already get through `/api/resource` or `frappe.client.get_list` | **not a finding** |
| an empty list, or only rows of the caller | **not a finding** |

The line between the second and third rows is whether the value belongs to somebody.

**For a read endpoint, the body decides the verdict, not the status.** A 200 is the normal
response. The question is only whether the body holds a value that the caller must not see.

## 8. Non-findings that look like findings

Each of these looks unguarded at the wrapper and is guarded. Compare your candidate with the
shape, not with a function name.

| Shape | Why it is guarded | Section |
|---|---|---|
| whitelisted `make_*` or `create_*` that returns or inserts the result of `get_mapped_doc(source_dt, source_name, ...)` | the mapper checks `read` on the source and `create` on the target | 1 |
| whitelisted function: `frappe.get_doc(dt, name)` with no check, changes fields, then `.save()` or `.submit()` | the document layer checks `write` or `submit` on that document | 1 |
| whitelisted function: `frappe.get_doc({...}).insert()` on a new document, for example a tree `add_node` | `insert()` checks `create` | 1 |
| whitelisted controller method on a doctype where only Administrator has `read` | the document load fails first | 2a |
| a function that is only a `frappe.enqueue` target, with no decorator | not an entry point | 2b |
| a wrapper whose check is one or two frames down, in the helper that gets the owning record or the parent | the finder did not follow the call | 1 |
| a read that returns a country, a timezone, a conversion factor, or other universal data | not the data of anybody | 7 |
| a read where each target doctype grants `read` at permlevel 0 to an automatic role that the actor has | the actor can read it by design | 6 |
| an operator payload against a parameter with a validated scalar annotation | pydantic rejects it with 417 | 4 |

When the inventory is available, `guard.class` on each entry point and the `refuted_by_framework`
list mark the first four shapes. Read `overridable_when` before you override one, and say in the
candidate which condition you think is true.

## 9. Read the installed dependency, not the pin

Whether an identifier injection through the query builder works depends on the installed `pypika`.
The escape is one function, `pypika.utils.format_quotes`: it doubles the quote character, or it
does not. Benches that pin the same commit can have different implementations installed, because
an environment that was not reinstalled keeps the old one.

**Refute by:** reading the installed function in the environment of the bench:

```
<bench>/env/bin/python -c "import inspect, pypika.utils; print(inspect.getsource(pypika.utils.format_quotes))"
```

State what you read and the pin in `frappe/pyproject.toml`. The finding is true only for the
installed implementation. Do not generalise in either direction.

The same rule applies to each sanitizer, serializer, or template engine: when a verdict depends
on how a dependency behaves, read the installed code.
