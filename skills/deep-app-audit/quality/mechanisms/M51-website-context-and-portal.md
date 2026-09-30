---
id: M51
---
# M51 — Website context and portal

**What:** Every portal page is rendered with a context dict. An app adds to that context and to
the portal navigation. `website_context` sets context keys from `hooks.py`.
`update_website_context` is a function that receives the context and may return a dict to merge
into it. `home_page`, `role_home_page`, `website_user_home_page` and
`get_website_user_home_page` choose the landing route. `portal_menu_items` and
`standard_portal_menu_items` add sidebar entries. `look_for_sidebar_json` turns on the
`sidebar.json` convention. `website_clear_cache` runs when the website cache is cleared.
`signup_form_template`, `comment_rate_limit` and `has_comment_permission` shape the login and
comment pages.

**Guards:** `website_context` collapses. The hook merge turns every value into a list, and the
website settings code then takes `[-1]` for every key except `top_bar_items`, `footer_items`
and `post_login`. A scalar therefore survives, and any other key an app sets to a list of its
own loses everything but the last item. The three exempt keys keep the merged list, so those
are the keys two apps can both add to.

The home page order is fixed and each step is last-wins: `get_website_user_home_page` if any
app declares it, else `website_user_home_page`, else a `role_home_page` entry for one of the
user's roles, else `home_page`. The result is cached per user.

`update_website_context` handlers all run, in app order, and the return value is merged into the
context. A handler that returns nothing changes nothing beyond what it wrote into the dict it
was given. `portal_menu_items` are added after the Portal Settings rows and the whole sidebar is
cached per user.

## Good use

An app sets a scalar context key from `hooks.py` and adds sidebar entries that merge.

```python
# hooks.py
website_context = {"favicon": "/assets/my_app/images/favicon.png", "splash_image": "/assets/my_app/images/splash.png"}

standard_portal_menu_items = [
	{"title": "Permits", "route": "/permits", "reference_doctype": "Permit", "role": "Permit Applicant"}
]
```

A value that must be a list goes in `top_bar_items` or `footer_items`, or it goes through
`update_website_context`, where the app builds the list itself:

```python
# hooks.py
update_website_context = "my_app.website.update_context"
```

```python
# my_app/website/__init__.py
def update_context(context):
	context.setdefault("my_app_links", [])
	context["my_app_links"] += [{"label": "Permits", "url": "/permits"}]
	return context
```

The handler adds to what is there. It runs on every portal page, for guests too, so it stays
cheap and it does not raise when a key it expects is absent.

A home page hook answers for the whole site. An app declares one only when it owns the portal.

## Rules

- A26 — A hook handler returns what the call site expects.
- A27 — A handler for a last-wins hook must yield to the apps it does not own.
- B30 — Do not change a collection while you iterate it, and copy a shared object before you edit it.
- B42 — A template must render when a value is missing.
