---
id: B42
area: correctness
---
# B42 — A template must render when a value is missing

**Why:** A print format, an email template and a portal page run on every document, not on the
one the author tested. A chained attribute on an empty link field raises inside the render, and
the user sees a traceback instead of an invoice. In a scheduled mail the same failure stops the
whole run silently.

## Bad

```jinja
<p>{{ doc.customer_address.city }}</p>
<p>{{ doc.items[0].item_name }}</p>
<p>{{ frappe.get_doc("Customer", doc.customer).tax_id }}</p>
```

## Good

```jinja
{% set address = frappe.get_cached_doc("Address", doc.customer_address) if doc.customer_address else None %}
<p>{{ address.city if address else "" }}</p>
{% if doc.items %}<p>{{ doc.items[0].item_name }}</p>{% endif %}
<p>{{ frappe.db.get_value("Customer", doc.customer, "tax_id") or "" }}</p>
```

## Find

- `rg -n '\{\{\s*doc\.\w+\.\w+' ` in print formats, email templates and `templates/`.
- `rg -n '\{\{[^}]*\[0\]' ` for an index into a child table with no `if` above it.
- `rg -n '\{\{[^}]*\|\s*\w+\s*\}\}'` and check whether the value can be `None` before the
  filter runs.
- Print Format records with `standard = "No"`: read the `html` field the same way.
- `rg -n 'get_formatted\(' ` in templates. It is one of the helpers the restricted renderer
  keeps.

## Confirm

Jinja renders `None` as an empty string when the value is printed on its own, so a single
attribute is usually safe. The failure is a chain, an index, a filter that needs a value, or a
method call. The restricted renderer on develop passes primitives and a `SafeDoc` wrapper to
the template, so a template that calls an arbitrary controller method fails there even when it
worked before. Read the field and the helper only. A missing image file and a missing linked
document are the two cases a test on a full document never exercises.
