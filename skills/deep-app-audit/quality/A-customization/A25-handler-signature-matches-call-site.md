---
id: A25
area: customization
mechanism: M12
---
# A25 — A hook handler accepts every argument the call site passes

**Why:** The framework dispatches a hook in one of two ways, and the two fail differently. A
direct call, which `doc_events` uses, passes the arguments as the call site writes them, so a
handler with the wrong parameter list raises `TypeError` on every document of that DocType. A
call through `frappe.call`, which most other hook families use, first removes every keyword
argument the handler does not declare, so a handler with a wrong parameter name runs, receives
nothing for that parameter, and reads a default instead of the real value. The first failure is
loud on a save the user cannot connect to the app. The second failure is silent, and the wrong
answer is the one the app was written to prevent.

## Bad

```python
# my_app/hooks.py
doc_events = {"Sales Invoice": {"on_submit": "my_app.accounts.push"}}
has_permission = {"Project": "my_app.projects.permission"}
```

```python
# my_app/accounts.py
def push(doc, method, extra_context):  # direct call: TypeError on every submit
	...
```

```python
# my_app/projects.py
def permission(doc, user=None, permission_type=None):  # frappe.call: core passes ptype
	return permission_type != "delete"  # permission_type is always None, so this is always True
```

## Good

```python
# my_app/accounts.py
def push(doc, method=None):
	...
```

```python
# my_app/projects.py
def permission(doc, ptype=None, user=None, **kwargs):
	if ptype == "delete" and doc.status == "Closed":
		return False
	return True
```

## Find

- Collect every handler path in `hooks.py` and resolve it to a function.
- `doc_events` handlers: the parameter list must be `(doc, method=None)` or `(doc)`.
- `rg -n 'def \w+\(doc, method\)' --type py` for handlers with no default on `method`.
- Compare each other hook family against its call site in the framework source, name by name.
- A handler whose parameter name is a synonym of the name the call site uses, such as
  `permission_type` for `ptype`, `doctype_name` for `doctype`, or `req` for `request`.
- A handler with no `**kwargs` whose body reads a value the call site does not pass under that
  name.

## Confirm

Read the call site to learn which of the two paths dispatches the hook, because the finding is
different on each.

Direct call. `compose` calls a `doc_events` handler as `f(doc, method, *args, **kwargs)`, and as
`f(doc, **kwargs)` when the event passes no positional argument and the handler declares one
positional parameter only (`source:frappe/model/document.py:compose`). Both arities are valid on
develop. A third positional parameter, or a `method` parameter with no default, is always a
finding, because the call raises. An extra parameter with a default is not a finding.

Call through `frappe.call`. `frappe.call` builds the keyword arguments with `get_newargs`, which
keeps a keyword only when the handler declares it by that name, or when the handler declares
`**kwargs` (`source:frappe/__init__.py:get_newargs`). Positional arguments are passed unchanged,
so an arity error on a positional parameter still raises. Two consequences follow. A handler that
declares fewer keyword parameters than the call site passes is correct and is not a finding. A
handler that declares a parameter the call site does not pass under that name is a finding, and
the evidence is in the handler body: the parameter is read, and it always holds its default.
`get_newargs` also always removes `ignore_permissions` and `flags`, even when the handler
declares them.

`has_permission` handlers go through `frappe.call` with `doc=`, `ptype=`, `user=` and `debug=`
(`source:frappe/permissions.py:has_controller_permissions`). The public hooks documentation shows
a handler that names the parameter `permission_type`, which therefore never sees the permission
type.

`permission_query_conditions` handlers receive `user` as a positional argument and `doctype` as a
keyword argument. A link search query function receives six positional arguments, so a function
with fewer positional parameters raises on every keystroke.

`after_file_upload` receives `doc=` and must return the doc. See A26.
