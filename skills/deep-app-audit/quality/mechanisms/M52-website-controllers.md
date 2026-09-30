---
id: M52
---
# M52 — Website controllers and web forms

**What:** A DocType with a web view renders through its controller. `doc.get_context(context)`
adds to the context of the document page and may return a dict to merge. A module-level
`get_list_context` in the DocType module turns on the portal list page for that DocType. A Web
Form record ships as a standard file with an optional Python module that supplies
`get_context`, and with `.js` and `.css` siblings. `webform_include_js` and `webform_include_css`
add assets to a web form per DocType. `page_js` adds a script to a desk Page.

**Guards:** The portal list renderer refuses a DocType with `custom = 1`, because a custom
DocType has no module to import, so a custom DocType never gets a `get_list_context`. It also
refuses `Web Page`. `webform_list_context` is read with `[0]`: the first app that declares it
answers, and it is consulted only for a custom DocType whose Module Def is not itself custom.
`get_context` on a document page runs after the context already carries the document, so it
adds and does not replace. A portal page is served to guests as well as to logged-in users, so
its controller must not assume a session user.

## Good use

The controller of the app's own DocType supplies what its template needs.

```python
# my_app/my_app/doctype/permit/permit.py
class Permit(WebsiteGenerator):
	def get_context(self, context):
		context.no_cache = 1
		context.lines = frappe.get_all(
			"Permit Line", filters={"parent": self.name}, fields=["item", "qty"], order_by="idx"
		)
		return context
```

The method reads the fields the template needs and nothing more. It returns the context.

The list page is turned on by a module-level function in the same module:

```python
def get_list_context(context=None):
	context.update({"title": _("Permits"), "row_template": "templates/includes/permit_row.html"})
```

A web form is shipped as a file, with its Python module beside it, so the logic is in version
control and can be tested. A web form submits straight to the server, so every rule the app
depends on is enforced in the controller, not in the web form script. The same is true of a
portal page that creates documents.

## Rules

- A30 — Do not ship code for a DocType created with `custom=1`.
- A20 — A rule that must always hold does not live in a Client Script.
- A26 — A hook handler returns what the call site expects.
- B42 — A template must render when a value is missing.
