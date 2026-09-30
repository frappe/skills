---
id: A27
area: customization
mechanism: M48
---
# A27 — A handler for a last-wins hook must yield to the apps it does not own

**Why:** Some hooks take the last app's value and drop the rest. Some take the first handler that
returns a value. A handler that answers for every input takes the whole feature away from every
other app on the bench, and the loss is silent.

## Bad

```python
# my_app/hooks.py
pdf_generator = "my_app.print.generate"
website_path_resolver = "my_app.website.resolve"
```

```python
# my_app/print.py
def generate(print_format=None, html=None, options=None, output=None, pdf_generator=None):
	return render_with_my_engine(html, options)
```

## Good

```python
# my_app/hooks.py
pdf_generator = "my_app.print.generate"
```

```python
# my_app/print.py
def generate(print_format=None, html=None, options=None, output=None, pdf_generator=None):
	if pdf_generator != "my_engine":
		return None
	return render_with_my_engine(html, options)
```

## Find

- `rg -n 'pdf_generator|pdf_body_html|pdf_header_html|pdf_footer_html|get_print_format_template|website_path_resolver|send_sms|send_token_via_sms|welcome_email|make_email_body_message|standard_queries' hooks.py`.
- For `pdf_generator`, a handler with no early `return None`.
- For any of these keys, the same key in a second app on the bench.

## Confirm

`get_pdf_with_hooks` calls every `pdf_generator` hook in order and returns the first truthy
result (`frappe/utils/print_utils.py`). A handler that ignores the `pdf_generator` name and
always returns a PDF wins for every generator, including the ones other apps own.

`website_path_resolver`, `send_sms`, `welcome_email`, `pdf_body_html`, and `standard_queries` take
the last app's value only (`[-1]`). Two apps that define the same key is a finding even when both
handlers are correct, because only one runs.

`website_context` collapses to the last value for every key except `top_bar_items`,
`footer_items`, and `post_login`, which are lists that merge.

A `page_renderer` class must define both `can_render` and `render`. A class missing either is
skipped with no message.

A last-wins hook in an app that is the only app on the bench is a weak finding today and a real
one the moment a second app is installed.
