---
id: M48
---
# M48 — Print and PDF

**What:** An app changes printed output at four points. A Print Format record, shipped as a
standard file, holds the HTML or the layout for one DocType. `get_print_format_template`
returns a compiled template for the print view. `pdf_body_html`, `pdf_header_html` and
`pdf_footer_html` render the parts of a wkhtmltopdf document. `pdf_generator` supplies a whole
PDF engine. `on_print_pdf` runs before the default engine. The controller method `before_print`
prepares the document for printing.

**Guards:** `get_print_format_template`, `pdf_body_html`, `pdf_header_html` and
`pdf_footer_html` read `[-1]` only: the last app on the bench answers, and every other app's
handler is dropped. `pdf_generator` is different. Frappe calls each handler in order and takes
the first truthy result, so a handler that answers for a generator name it does not own takes
printing away from the app that does own it. The whole `pdf_generator` loop is skipped when the
requested generator is `wkhtmltopdf`. `on_print_pdf` runs only when no generator returned a
PDF. A print template renders in the sandboxed Jinja environment against every document of the
DocType, not against the one the author tested.

## Good use

A `pdf_generator` handler tests the name it was given and returns `None` for every other name.

```python
# hooks.py
pdf_generator = "my_app.print.generate"
```

```python
# my_app/print.py
def generate(print_format=None, html=None, options=None, output=None, pdf_generator=None):
	if pdf_generator != "my_engine":
		return None
	return render_with_my_engine(html, options)
```

This is what makes several PDF engines able to live on one bench.

For the HTML hooks there is no such yielding. Two apps that both set `pdf_body_html` is a
defect on the bench, not a merge. An app that only needs a different layout for its own
DocTypes ships a Print Format instead, and makes it the default with a Property Setter on
install.

A Print Format lives in the app tree with its JSON, so the file is the record and a review can
read it:

```
my_app/my_app/print_format/permit_certificate/permit_certificate.json
```

The template reads fields and helpers. Every chained attribute, every index into a child table
and every filter that needs a value is guarded, because a print format runs on the document
with the empty link field too.

## Rules

- A27 — A handler for a last-wins hook must yield to the apps it does not own.
- A26 — A hook handler returns what the call site expects.
- A31 — Set the app's print format as the default with a Property Setter on install.
- A40 — Ship a report, print format, or web form as a standard file in the app.
- A32 — A template reads data. Logic belongs in a `jinja` hook method.
- B42 — A template must render when a value is missing.
