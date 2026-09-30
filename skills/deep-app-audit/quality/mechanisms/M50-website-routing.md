---
id: M50
---
# M50 — Website routing

**What:** A request to a portal path is turned into a page by `PathResolver`. An app adds to
that in several ways. A file under `www/` or `templates/pages/` becomes a route. `website_route_rules`
maps a dynamic route to a static endpoint. `website_redirects` adds redirect rules.
`website_generators` gives a DocType a web view. `base_template` and `base_template_map` choose
the outer template. `page_renderer` adds a renderer class. `website_path_resolver` replaces the
path resolution step.

**Guards:** Two of these are sharp.

`website_path_resolver` is not a chain. The resolver loop assigns the endpoint on each pass, so
only the last app's resolver decides the endpoint; the earlier ones run and their results are
thrown away. When any app declares the hook, the built-in `resolve_path` does not run at all, so
the home page lookup, the `.html` suffix handling, the `website_route_rules` map and the
werkzeug redirects are all the new resolver's job.

A `page_renderer` class must have both `can_render` and `render`. A class missing either is
skipped, and the only sign is a message on the console of the process that loaded it. Custom
renderers are tried before every built-in renderer, so a `can_render` that answers `True` too
widely takes over static files, web forms, document pages and print.

Redirect rules are regular expressions matched against the path, and the result is cached per
path in Redis. A rule that does not compile is logged and the request continues. Route rules
from `website_route_rules` are merged with the routes of every DocType that has a web view, and
the merged list is cached outside a development server.

## Good use

An app adds pages by adding files. A page at `my_app/www/permits/index.html` answers
`/permits`. A sibling `index.py` supplies the context. This needs no hook and collides with
nothing.

A renderer is for a path space the app owns, and `can_render` answers only for that space:

```python
# hooks.py
page_renderer = ["my_app.renderers.PermitPage"]
```

```python
# my_app/renderers.py
from frappe.website.page_renderers.base_renderer import BaseRenderer


class PermitPage(BaseRenderer):
	def can_render(self):
		return self.path.startswith("permit/")

	def render(self):
		...
```

`can_render` is cheap and it returns a boolean. It runs on every portal request, before the
built-in renderers.

A redirect belongs in `website_redirects` when the app owns it and in Website Settings when the
site owns it. Both sources are merged, so an app does not need to write site rows.

`website_path_resolver` is a whole-bench decision. An app declares it only when it replaces
portal routing for the site, and never as a way to add one route.

## Rules

- A27 — A handler for a last-wins hook must yield to the apps it does not own.
- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve.
- A24 — A `hooks.py` value is static data, computed once per process.
