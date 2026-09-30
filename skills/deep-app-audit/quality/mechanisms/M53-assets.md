---
id: M53
---
# M53 — Desk and website assets

**What:** `app_include_js`, `app_include_css` and `app_include_icons` add files to every desk
page. `web_include_js`, `web_include_css` and `web_include_icons` add files to every website
page. `sounds` registers sound files the desk can play. All of them take bundle paths under
`/assets/<app>/`.

**Guards:** These lists are merged across apps and every entry is loaded on every page of its
kind, for every user, whether the feature is used or not. Desk also merges `app_include_js` and
`app_include_css` from the site config, so a site can add to the list an app declares. The cost
is on the client: no server metric shows it. A file served from the app's `public` directory is
served by the web server, while a file under `www` needs a Python worker.

## Good use

The app puts on every page only what every page needs, such as a navbar item, a global keyboard
shortcut or a small utility namespace.

```python
# hooks.py
app_include_js = ["my_app.bundle.js"]
doctype_js = {"Delivery Note": "public/js/delivery_note.js"}
```

Everything that belongs to one DocType goes in `doctype_js`, `doctype_list_js` or the DocType's
own script file, so it is loaded with that form and nowhere else.

A heavy library is loaded when the user asks for the feature:

```javascript
frm.add_custom_button(__("Show Route"), () => {
	frappe.require("/assets/my_app/js/map_widget.bundle.js", () => {
		my_app.show_route(frm);
	});
});
```

Website assets follow the same rule, and the audience there is wider: `web_include_js` is
downloaded by every visitor of every portal page, including a guest who reads one article.

Static files live under the app's `public` directory.

## Rules

No rule in the knowledge base covers this mechanism yet.
