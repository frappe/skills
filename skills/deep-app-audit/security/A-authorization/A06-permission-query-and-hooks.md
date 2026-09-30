# A06 — Permission query conditions and `has_permission` hooks

**Scope:** the machinery that narrows list queries to what a user may see, and the registered
hooks that are supposed to enforce it.

**Why:** permission query conditions are the only row-level control on list views and reports. A
condition that is skipped exposes every row. A hook that is registered but returns nothing reads
as protection during review, which makes that failure worse than having no hook at all.

## Find — query conditions
- `permission_query_conditions` hooks in `hooks.py` — for each, read the function: does it
  return a condition for every case, or can it return an empty string / `None` and so match
  everything?
- `get_match_cond`, `build_match_conditions`, `get_permission_query_conditions` call sites.
- `rg -n "ignore_ifnull|ignore_permissions|user=.*Administrator" ` inside query paths.
- Doctype name casing: `get_list("sales invoice")` vs `"Sales Invoice"` — check that a
  mismatched casing does not skip the condition.
- `parent_doctype` / `parenttype` supplied by the client when querying child tables.

## Find — hook sanity
Collect every `has_permission` and `permission_query_conditions` entry from `hooks.py`, resolve
each target function, and check:
- Does it exist and import cleanly?
- Can it return `True` / `""` / `None` on a path that should deny? An empty
  `permission_query_conditions` string means "no restriction".
- Does it handle the `user=None` case (which means the session user) correctly?
- Does it handle Administrator, Guest, and Website User distinctly?
- Is it registered for the doctype it actually guards, spelled correctly?
- The inverse: doctypes that clearly need a query condition and have none.

## Confirm
- Test the reasoning against a Website User and a plain System User, not Administrator.
- Shared documents (`DocShare`) must widen the condition, never replace it.
- A noop hook is only a finding when you can name the rows it fails to hide. Reach them.

## Report
For each bypass, give the `get_list` call that returns rows the actor should not see. For a
failing hook, name the hook, the doctype, and quote the path that returns no restriction.
