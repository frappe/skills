# Fix template and code injection in a Frappe app

Three shapes, one root: **a user decides what code the server runs.** A Jinja template is code, a
formula is code, and a dotted path is a choice of code. The fix is a combination of three controls —
**restrict** what the code can reach, **gate** who may author it, and **allow-list** what may be
called — and it takes all three, because restriction alone still leaves reads open.

## Steps

### 1. Name the author and the reader

For the vulnerable call, find (a) every role that can **write** the template, formula or path — read
the DocPerms of the doctype holding the field, and remember import, REST and `db_set` all write past
form validation — and (b) every role that can **read** the result, including a whitelisted "preview"
or "test" method.

Done when: both lists exist. If the author set is already "System Manager only" and the reader set is
the same, the finding is likely by-design. Record why and stop.

### 2. Apply the fix for the shape

**A user-writable template rendered with `frappe.render_template`:**

```python
validate_template(doc.body, restrict_globals=True)               # at save, same mode as render
frappe.render_template(doc.body, context, restrict_globals=True)
```

- Pass `restrict_globals=True` **explicitly, at both calls.** `None` is not "restricted": it follows
  the site config key `disable_render_safe_exec`, so behaviour varies per site.
- **Clean the context.** Remove modules, `frappe` / `frappe.utils`, and whole `Document` objects —
  `{"frappe": frappe.utils}` re-exports what restriction took away. Pass the fields the template
  needs (`frappe.get_cached_value(...)`, not `frappe.get_doc(...)`).
- Keep `safe_render=True` (the default) for user input. `False` disables the `".__"` check.
- Pass user text as template *content* only. Where a call accepts a path, a one-line value ending in
  `.html`, `.md` or `.txt` is loaded **as a file path**.

**Then gate authorship.** Restricted globals still allow an arbitrary `SELECT` (`frappe.db.sql` is
exposed read-only) and a `frappe.get_all` that ignores permissions. So when a low-privilege role can
both write the template and read the output, add `frappe.only_for("System Manager")` (or the
narrowest admin role) to the method that creates or previews it. Print Formats are Jinja: creating
one is authoring code.

**A formula evaluated with `safe_eval`:** pass a closed function table and the row values as
**locals**, no globals, and validate the formula's AST at save:

```python
frappe.safe_eval(formula, eval_globals=None, eval_locals={**row_values, **FORMULA_FUNCTIONS})
```

Reserve `safe_exec` for authors already trusted to write Server Scripts.

**A caller-supplied dotted path:** `frappe.get_attr` and `frappe.call(str)` check only that the
path's root app is installed — any module-level callable in any app is reachable. Prefer a fixed
`dict` allow-list. Where the set is open, require a whitelisted function, and check **at save and at
run**:

```python
def resolve_whitelisted_method(api_path):
	method = frappe.get_attr(api_path)
	frappe.is_whitelisted(method)
	if "GET" not in frappe.allowed_http_methods_for_whitelisted_func.get(method, ()):
		frappe.throw(_("Method {0} must permit GET requests").format(frappe.bold(api_path)), frappe.PermissionError)
	return method
```

For `doc.run_method(name)` or `getattr(doc, name)()` with `name` from the request, check
`doc.is_whitelisted(name)` first (`run_doc_method` does this. `Document.run_method` does not).

Done when: every call site that renders, evaluates or dispatches on the user value carries the fix —
grep the doctype's field name and the method name across the app. Template injection is rarely in
one place.

### 3. Verify

As the lowest author role, write each payload and trigger every path that renders it (preview, send,
print, scheduled job):

- `{{ frappe.db.sql("select name from tabUser limit 1") }}` — must not return data to a role that
  cannot read User.
- `{{ frappe.sendmail }}`, `{{ frappe.db.set_value }}` — must be undefined.
- `{{ ''.__class__ }}` — must throw "Illegal template".
- An invalid template — must be refused at save.
- For dispatch: `frappe.utils.get_site_path` and `frappe.get_installed_apps` (real, non-whitelisted
  callables) — refused at save **and** at run.

Start with the known-positive control
([verify.md](../verify.md)): every payload must succeed
on the pre-fix code first.

Done when, on every release line: every payload succeeded before and is refused after, on every
render path from step 2.

## References

- Escaping user data *inside* a trusted template is XSS, not this class:
  [classes/xss.md](xss.md).
- Shipping, backports and the public PR: [the security workflow](../workflow.md).
