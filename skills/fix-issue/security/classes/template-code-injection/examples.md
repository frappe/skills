# Published template and code-injection fixes

## A user-writable email body rendered with full globals — GHSA-qq49-v74j-hjh7

`erpnext/accounts/doctype/process_statement_of_accounts/process_statement_of_accounts.py`.
Fix: [frappe/erpnext#56458](https://github.com/frappe/erpnext/pull/56458). Restricted at save and at
render, and `frappe.utils` removed from the context.

```diff
-		validate_template(self.body)
+		validate_template(self.body, restrict_globals=True)
 	return {
 		"doc": template_doc,
 		"customer": frappe.get_doc("Customer", customer),
-		"frappe": frappe.utils,
 	}
-			message = frappe.render_template(doc.body, context)
+			message = frappe.render_template(doc.body, context, restrict_globals=True)
```

## The same shape in six sibling call sites — GHSA-6w83-8777-v93q

Request for Quotation supplier email, and five more templates of the same kind.
Fix: [frappe/erpnext#57899](https://github.com/frappe/erpnext/pull/57899).

```diff
-		rendered_message = frappe.render_template(message_template, doc_args)
+		rendered_message = frappe.render_template(message_template, doc_args, restrict_globals=True)
```

## Authoring a Jinja Print Format through a whitelisted method — GHSA-w996-r7v3-87wr

Fix: [frappe/erpnext#55708](https://github.com/frappe/erpnext/pull/55708). The method that created
a Print Format gained `frappe.only_for("System Manager")`: the authorship gate, because a print format
body is a template.

## A caller-supplied method path (CWE-470) — GHSA-794x-fhm7-58j7

`erpnext/accounts/doctype/financial_report_template/financial_report_engine.py` (`_process_api_row`)
and `financial_report_validation.py`. Fix:
[frappe/erpnext#58697](https://github.com/frappe/erpnext/pull/58697). A report row's "Custom API"
field went straight to `frappe.call`. The fix resolves it through `get_valid_api_method` (see
[template-code-injection.md](../template-code-injection.md)) at both validation and run time.

```diff
 	def _process_api_row(self, row) -> RowData:
 		api_path = row.calculation_formula
-		# TODO
+		method = get_valid_api_method(api_path)
 		try:
-			values = frappe.call(api_path, filters=self.context.filters, periods=self.period_list, row=row)
+			values = frappe.call(method, filters=self.context.filters, periods=self.period_list, row=row)
```

In the validator, `module = frappe.get_module(path); hasattr(module, name)` — which proves only that
the name exists — was replaced by the same `get_valid_api_method`.
