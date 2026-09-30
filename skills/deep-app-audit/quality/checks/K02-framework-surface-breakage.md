---
id: K02
---
# K02 — Framework surface breakage

**Kind:** whole-surface check over the framework surface one app touches. In one pass over the
app it finds the guards the app goes around, and the symbols, arguments, hook keys, call targets,
tables and columns that `develop` has deprecated, removed or changed. Each finding carries the
version range in which its effect differs, taken from core's own git history. It is not a rule,
because it covers many mechanisms and each one has its own shape, and because the same call is
correct on one version and wrong on another. It is not a lint pass, because a match is a
candidate and the core read point decides the verdict. It is not a migration guide, and it does
not repeat the migration wiki. It does not cover access control. It does not compare an override
method with the core method it shadows, which is `K01`.

**Why:** the framework keeps an invariant so that core code can rely on it. An app that goes
around the guard keeps the invariant's promise and loses its protection, and the failure appears
far from the cause. The framework also tells the app almost nothing about what it has dropped.
On `develop`, 35 of the 37 rows in `frappe/deprecation_dumpster.py` graduate at `v17`, and a
`v17` marker is a `PendingFrappeDeprecationWarning`, which the dumpster ignores at import
(`frappe/deprecation_dumpster.py:66`). The dev-server filter in `frappe/__init__.py:228-229`
raises Python's `DeprecationWarning` and `PendingDeprecationWarning`, which the Frappe classes do
not inherit. So a deprecated call prints nothing, and the app learns of the removal when the site
is already on the new version. The support corpus holds a submitted invoice with no ledger rows,
a boot that fails on a symbol a refactor removed, and a report broken by a renamed column. A
static read of the app is the only warning the app gets.

## Task

1. Fix the direction and the reference. The check reads the app forward against `develop`. The
   reference is `frappe` at the bench revision, plus every app the target names in
   `required_apps` or imports, each with full git history and a remote-tracking `develop`. Record
   `git rev-parse HEAD` per app, because a finding is a statement about one revision. No second
   checkout is read: an older-version consequence is a column derived from the history of
   `develop`, not a second pass.
2. Inventory the app's framework surface in one parse.
   - `hooks.py`. Parse with `ast` and read the module-level assignments with `literal_eval`. Do
     not import the file, because an import runs app code. Record every key, and every dotted
     string inside the values.
   - Python imports and attribute chains. Parse every `.py` file with `ast`, record every
     `from frappe... import name` and every attribute chain rooted at a name bound to a framework
     module, and resolve `as` names. A leaf-name search must not be used: leaves such as `_`,
     `main`, `txt` and `send_mail` match licence headers and app code.
   - Client call targets: every `method:` string in the app's `.js`, `.ts`, `.vue` and `.json`
     files, and every dotted argument of `frappe.call`, `frm.call` and `frappe.xcall`.
   - Tables and columns: every `` `tab<DocType>` `` name in a `frappe.db.sql` string, every
     `frappe.qb.DocType("...")` argument, and the columns each is read or written with.
   - Mechanism use: the DocType JSON files, the controller classes, `patches.txt`, `fixtures/`,
     and `<module>/custom/*.json`.
3. Build the guard table from the mechanism inventory. One row per guard, with the mechanism, the
   core read point as a file and line, the invariant, the bypass shape, and the runtime effect:
   silent, warned, or raised. The families in step 6 are the minimum set.
4. Build the deprecation tables from the reference tree. Parse
   `frappe/deprecation_dumpster.py` with `ast` and walk the whole tree, not the module body,
   because some decorators sit inside a factory function. Every
   `@deprecated(original, marked, graduation, msg)` gives the old name, the mark date, the
   graduation version and the note; the file gives 37 rows. Deprecations of a parameter or of a
   behaviour do not use the decorator: find every `deprecation_warning(marked, graduation, msg)`
   call in the rest of the `frappe` tree with `ast` and record the enclosing callable; the tree
   gives 22 rows. Map each graduation to its effect through `__get_deprecation_class`: `v15`
   raises, `v16` warns, `v17` and an unrecognised string are silent.
5. Resolve every symbol at run time, not statically. Import the module with `importlib` in the
   bench environment and test the attribute with `hasattr`. A static parse is unsound, because
   `frappe/utils/__init__.py` and `frappe/tests/__init__.py` re-export through `import *`.
   Resolution is safe, because the decorator fires on a call and not on an attribute read, and it
   needs no site. Resolve `frappe.db.x` against `frappe.database.database.Database`, which is a
   thread-local, and resolve `frappe.qb` members against the query-builder module. A symbol in
   the table of step 4 is **deprecated**. A symbol that does not resolve is **removed**.
6. Run one pass per guard family.
   - **6a. Transaction control.** Find `frappe.db.commit` and `frappe.db.rollback` and follow each
     call site to the path that reaches it. A `doc_events` handler holds a warned no-op:
     `compose` raises `frappe.db._disable_transaction_control` around the hooked handlers
     (`frappe/model/document.py:2080-2091`) and `commit` then warns and returns
     (`frappe/database/database.py:1197-1198`). It is still a defect, because the commit the app
     intended never happens. A controller lifecycle method, an `override_doctype_class` method,
     an `extend_doctype_class` method, or a function one of them calls, holds a real commit:
     `compose` calls the controller method outside the counter. `frappe.db.rollback(save_point=…)`
     is not a finding, because the save-point branch runs before the guard test
     (`frappe/database/database.py:1217-1220`).
   - **6b. Override that does not call the parent.** An `override_doctype_class` or
     `extend_doctype_class` method that shadows a core method and holds no `super()` call removes
     a core step. `K01` reads this surface in full; `K02` records the site and its effect.
   - **6c. Override that core does not consult.** `override_whitelisted_methods` applies at RPC
     dispatch, in the mapper, and in treeview only. A core caller that imports the target
     directly is not redirected, and the evidence is that direct import in a core app.
   - **6d. Hook shape the read point cannot use.** A `hooks.py` value that is a function, a class
     or a module is dropped by `_is_valid_hook`. A `doc_events` handler must accept
     `(doc, method)` or `(doc)`. A hook whose read point uses the return value must return it:
     `after_file_upload` returns the document, `override_doctype_dashboards` the dict,
     `update_website_context` the context, and a `pdf_generator` hook returns `None` for a
     generator it does not own. A `page_renderer` class needs both `can_render` and `render`.
   - **6e. Guard bypassed by the sync path.** Customize Form refuses a change that
     `allow_property_change` blocks, and refuses a core, Single or custom DocType. The `custom/`
     folder sync and `make_property_setter` in code reach the same records with no such test, and
     the `custom/` sync inserts Custom Fields with `ignore_validate`. A finding is a Property
     Setter or a Custom Field, in code, in `custom/*.json` or in `fixtures/`, that turns `reqd`
     off, turns `read_only` off, turns `allow_on_submit` on, changes `options`, changes a
     fieldtype outside `ALLOWED_FIELDTYPE_CHANGE`, or targets a DocType in `core_doctypes_list`.
   - **6f. Code that no read point loads.** A DocType with `custom: 1` always gets the `Document`
     or `NestedSet` class, and desk skips its form JS, its HTML templates and its dashboard. A
     Virtual DocType controller must implement `db_insert`, `db_update`, `load_from_db` and
     `delete`, and must not depend on `frappe.get_all`, bulk fetch, lazy loading, or
     frappe-managed child rows.
   - **6g. Last-wins hooks with more than one owner.** App order decides the winner, and app order
     is a site fact. A finding is a hook that reads `[-1]` and that two installed apps declare:
     `override_doctype_class` for one DocType, `website_path_resolver`, `send_sms`,
     `welcome_email`, `pdf_body_html`, `get_print_format_template`, and `standard_queries` for
     one DocType.
   - **6h. Mechanisms with no read point.** An assignment to an attribute of an imported framework
     module is a monkey patch. An assignment to a `frappe.local` proxy, such as `frappe.db` or
     `frappe.flags`, replaces per-request state. Neither has an ordering guarantee.
7. Test the argument and behaviour rows of step 4 against the call sites, scoped to the callable
   the warning sits in and never to the parameter name alone. `limit_start` is deprecated on
   `frappe/model/qb_query.py:156`, which only `frappe/desk/reportview.py` uses; the same keyword
   on `frappe.get_all` reaches `frappe/model/db_query.py:121` and is not deprecated. Then compare
   each call site with the live signature from `inspect.signature`. A keyword that the signature
   does not accept and does not absorb in `**kwargs` is **changed**, and it is a `TypeError` at
   run time.
8. Test every hook key the app declares against the keys `develop` reads. Build the read set from
   four sources over `frappe` and every other core app on the bench: the literal argument of
   `frappe.get_hooks("<key>")`, the literal key of `hooks.get("<key>")` and
   `get_hooks().get("<key>")`, the attribute name in `app_hooks.<key>`, and the module-level
   assignments of each core app's own `hooks.py`. One source is not enough; all four together
   report nothing on a healthy first-party app. A key outside the read set is **dead**. Report
   the app metadata keys, such as `app_publisher` and `source_link`, separately, because they are
   data and not hooks.
9. Resolve every dotted hook value and every client call target by import and attribute read. An
   unresolved value is **removed**. `frappe.get_attr` raises `AppNotInstalledError` for an unknown
   app, and `sync_jobs` drops a scheduler row with a warning when the method is missing. For a
   client call target, also test membership of `frappe.whitelisted` after the import: a target
   that resolves and is not whitelisted is **changed**, and it is an HTTP 403 at run time.
   Whitelist state and deprecation are independent.
10. Test every table and column of step 2 against the DocType JSON of the reference tree. Index
    every `<name>/<name>.json` under a `doctype/` directory whose `doctype` field is `DocType`.
    A named table with no core DocType belongs to the app itself and is not a finding. A named
    column the DocType does not carry is **removed**. Record every core table the app names, with
    its owning app and its column list, as the coupling surface.
11. Date every finding against core's git history, and derive the version range from it. For a
    removed symbol, `git log -S'<symbol>' -- <the module it lived in>` names the removing commit
    and `git tag --contains <commit>` names the first release that holds it. For a guard, the
    same two commands on the guard's read point give the release from which the effect changed:
    the `doc_events` transaction guard is commit `638dbb6bc`, dated 2024-03-06, first released in
    `v16.0.0`, so a `commit` in a handler is a warned no-op from `v16` and a real partial commit
    before it. Both readings are defects, and they are different defects.
12. Test reachability for every candidate. The entry points are: every `@frappe.whitelist`
    function; every dotted value in `hooks.py`; the lifecycle and duck-typed method names of the
    mechanism inventory, which include `has_website_permission`, `get_context`, `get_list`,
    `get_count`, `get_stats` and `get_timeline_data`; every entry in `patches.txt`; every
    `scheduler_events` method; every report `execute`; and every dotted string in the app's
    `.js`, `.json`, `.html` and `.txt` files. The closure follows called names over the app's
    function definitions. Keep the closure conservative: a name that appears anywhere in the
    app's non-Python files counts as an entry point, and test files stay out of the graph. On a
    first-party app this leaves about 2 percent of definitions unreachable, and that residue is
    duck-typed framework names.
13. Report an unreachable match only where a false negative is expensive, which is where the guard
    is irreversible or silent. These are transaction control (6a), an override that never calls
    `super()` (6b), and a monkey patch or a replaced `frappe.local` proxy (6h), because each one
    becomes live the day a caller appears and none of them announces itself. Every other
    unreachable match stays out of the result table. The reachability column is kept for the rows
    that remain, because the closure matches on name and declares reachable code unreachable when
    the caller is dynamic.
14. Confirm each candidate at the core read point named in the guard table, not against the guard
    table text. The read point is a file and a line on the bench revision, and it decides whether
    the guard applies to this app.
15. Rank by run-time consequence, not by graduation version. The order is: a removed symbol or an
    unresolved hook value on a path that boot or migrate reaches; a removed symbol elsewhere; a
    guard that fails silently; a changed signature or a lost whitelist; a guard whose effect
    differs across the versions the app supports; a missing column; a guard that warns; a
    deprecated symbol that raises; a guard that raises at install or at migrate; a deprecated
    symbol that warns; a deprecated symbol that is silent. A silent `v17` deprecation is the
    largest group and the least urgent, and it must not crowd out the first rows.

Server Scripts, Client Scripts, Property Setters and Custom Fields created from the desk live in
the site database, and this check reads the app tree and its git history only. A Server Script
that calls a removed symbol, or that commits from a DocType Event, is out of reach unless the app
ships it as a fixture file. The `## Output` states that gap, because a clean result covers the
app's files and not the site.

## Inputs

- The app tree, with its `hooks.py`, its Python, JavaScript and JSON files, its DocType JSON, its
  `patches.txt`, its `fixtures/` and its `<module>/custom/*.json`.
- Checkouts of `frappe` and of every core app the app depends on, at the bench revision, each with
  full git history and a remote-tracking `develop`.
- `frappe/deprecation_dumpster.py` and the `deprecation_warning` call sites of the reference tree.
- The bench Python environment, so that `importlib`, `inspect.signature` and `frappe.whitelisted`
  answer at run time. `import frappe` succeeds with no site.
- The mechanism inventory guard table, with a core read point for every row.
- The installed app list in site order, because app order decides every last-wins hook. Without
  it, step 6g reports nothing.

## Output

| Column | Content |
|---|---|
| Surface | `guard`, `symbol`, `argument`, `hook key`, `hook value`, `client call`, `table`, or `column` |
| Name | The guard, or the dotted symbol, hook key, target, table or column the app uses |
| Mechanism | Mechanism inventory row number. Empty when the finding is not about a mechanism |
| Read point | Core file and line that keeps the guard, or that holds the deprecation |
| App site | App file and line |
| Shape | Which shape of step 6, or which of `deprecated`, `removed`, `changed`, `dead` |
| Effect on develop | `raises`, `warns`, `silent`, or `no-op` |
| Versions affected | The version range in which the effect differs from `develop`, from step 11. Empty when every version behaves the same |
| Evidence | The dumpster row, the `deprecation_warning` site, the removing or guard commit, or the signature |
| Replacement | The name the note or the commit gives. Empty when there is none |
| Reachable | `yes`, `no`, or `dynamic` |
| Verdict | `broken`, `at risk`, or `not applicable`, with the reason from step 14 |

The table covers the app tree only. It says nothing about the Server Scripts, Client Scripts and
Property Setters of any site the app is installed on.

A second table holds the coupling surface: one row per core DocType the app reads with raw SQL or
the query builder, with the owning app, the column list and the count of app sites. A table the
app reads today with no missing column is still a schema the app does not own.

A third table holds one count per `Surface` and `Shape` pair. That table shows whether one shared
helper carries the whole finding, or whether the app breaks the surface in many places.
