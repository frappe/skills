---
id: M47
---
# M47 — Jinja environment and templates

**What:** The `jinja` hook adds names to the template environment. `jinja = {"methods": [...]}`
adds globals a template can call. `jinja = {"filters": [...]}` adds filters. Each entry is a
dotted path to a module or to a function: a module path registers every function in the module,
a function path registers that one function. The template loader lists the apps in reverse
order with frappe last, so a template file in an app shadows a template of the same path in
frappe. `template_apps` replaces that app list.

**Guards:** The environment is a `SandboxedEnvironment` with the unsafe attribute set of
`safe_exec`, so a template cannot reach private attributes or dunder methods. Globals come from
`get_safe_globals`, or from the smaller `render_safe_globals` when restricted rendering is on.
The environment is built once per site and cached, and the loader is cached with it, so a new
template file or a new hook entry needs a cache clear. Registration is by function name only:
two apps that register a function of the same name collide, and the last app wins. The old
`jenv` hook is gone; it registers nothing.

## Good use

The app registers named functions and keeps the logic in Python.

```python
# hooks.py
jinja = {
	"methods": ["my_app.utils.jinja_methods.get_permit_lines"],
	"filters": ["my_app.utils.jinja_filters.as_permit_no"],
}
```

```python
# my_app/utils/jinja_methods.py
import frappe


def get_permit_lines(permit: str) -> list[dict]:
	"""Return the lines of a permit as plain dicts."""
	return frappe.get_all("Permit Line", filters={"parent": permit}, fields=["item", "qty"], order_by="idx")
```

The function name is the name the template uses, so the name carries the app in it or is
specific enough that no other app chooses it. `get_lines` is a collision waiting to happen;
`get_permit_lines` is not.

The function returns plain data: strings, numbers, dicts and lists. The template reads that
data and formats it. A template that calls controller methods or walks object attributes breaks
when restricted rendering is on.

A template that overrides a frappe template keeps the same path under the app, for example
`my_app/templates/includes/footer/footer_powered.html`. The override is total: every page that
includes the path gets the app's file, on every site where the app is installed.

## Rules

- A32 — A template reads data. Logic belongs in a `jinja` hook method.
- B42 — A template must render when a value is missing.
- B39 — Decode once at the boundary and encode once at the output.
- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve.
