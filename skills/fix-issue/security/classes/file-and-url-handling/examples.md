# Published file, path and URL fixes

## Path traversal

**Static files — GHSA-xj39-3g4p-f46v.** `frappe/middlewares.py`, `StaticDataMiddleware`. Fix:
[frappe/frappe#34651](https://github.com/frappe/frappe/pull/34651). The same shape in
`website/page_renderers/static_page.py` was GHSA-v4wg-gqfr-rpjm
([#34396](https://github.com/frappe/frappe/pull/34396)).

```diff
-	path = os.path.join(directory, site, "public", "files", cstr(path))
-	if os.path.isfile(path):
-		return os.path.basename(path), self._opener(path)
+	files_path = Path(directory) / site / "public" / "files"
+	path = (files_path / Path(cstr(path))).resolve()
+	if not path.is_relative_to(files_path) or not path.is_file():
+		raise NotFound
+	return path.name, self._opener(path)
```

**App includes — GHSA-67rf-pxgh-vfqv.** `frappe/model/utils/__init__.py`, `render_include`. Fix:
[frappe/frappe#38215](https://github.com/frappe/frappe/pull/38215).

```diff
-	with open(frappe.get_app_path(app, app_path), encoding="utf-8") as f:
+	resolved_path = os.path.realpath(frappe.get_app_path(app, app_path))
+	app_root = os.path.realpath(frappe.get_app_path(app))
+	if not resolved_path.startswith(app_root + os.sep):
+		frappe.throw(frappe._("Security Error: The Path provided is not safe."))
+	with open(resolved_path, encoding="utf-8") as f:
```

**Backup download — GHSA-w4p4-fp9m-47gj.** `frappe/utils/response.py`, `download_backup`. Fix:
[frappe/frappe#38740](https://github.com/frappe/frappe/pull/38740), which added `check_path_safety`.

```diff
+	filename = path.split("/backups/", 1)[1]
+	backup_path = frappe.get_site_path("private", "backups")
+	requested_path = frappe.get_site_path("private", "backups", filename)
+	if not check_path_safety(base_path=backup_path, requested_path=requested_path):
+		frappe.throw(_("Invalid backup path"), frappe.PermissionError)
 	return send_private_file(path)
```

**Email inline images — GHSA-8v98-cfpm-9p67.** `frappe/email/email_body.py`,
`get_filecontent_from_path`. Fixes: [#41325](https://github.com/frappe/frappe/pull/41325) and
[#41348](https://github.com/frappe/frappe/pull/41348) (which made `File.get_content` call
`validate_file_path()` at read time).

```diff
 	elif path.startswith("private/files/"):
-		full_path = frappe.get_site_path(path)
+		base_path = os.path.abspath(frappe.get_site_path("private", "files"))
+		full_path = os.path.abspath(frappe.get_site_path(path))
 	else:
-		full_path = path
+		return None
+	if os.path.commonpath((base_path, full_path)) != base_path:
+		return None
```

**A path built from `file_url` — GHSA-6ffr-92hr-3394.** `serial_and_batch_bundle.py`,
`get_serial_batch_from_csv`. Fix: [frappe/erpnext#53460](https://github.com/frappe/erpnext/pull/53460).
This removes the traversal. `find_file_by_url` would also authorise the read.

```diff
-	if "private" in file_path:
-		file_path = frappe.get_site_path() + file_path
-	else:
-		file_path = frappe.get_site_path() + "/public" + file_path
-	with open(file_path) as f:
-		reader = csv.reader(f)
+	file = frappe.get_doc("File", {"file_url": file_path})
+	if file.file_type != "CSV":
+		frappe.msgprint(..., raise_exception=frappe.ValidationError)
+	csv_data = read_csv_content(file.get_content())
```

## Attachments — GHSA-fwrv-4rw4-97fw

`frappe/utils/file_manager.py`, `add_attachments`. Fix:
[frappe/frappe#39407](https://github.com/frappe/frappe/pull/39407).

```diff
 def add_attachments(doctype, name, attachments):
+	if not frappe.has_permission(doctype, "write", doc=name):
+		frappe.throw(_("You need write permissions to add attachments to this record."))
 	for a in attachments:
 		if isinstance(a, str):
+			if not frappe.has_permission("File", ptype="read", doc=a):
+				frappe.throw(_("You don't have permission to read/attach the file {0}.").format(a))
```

## SSRF

**Remove the capability — GHSA-m4m4-j2m2-7fcw.** `erpnext/edi/doctype/code_list/code_list_import.py`.
Fix: [frappe/erpnext#54137](https://github.com/frappe/erpnext/pull/54137). Remote URLs are no longer
accepted from the request.

```diff
-	if (file_url := frappe.local.uploaded_file_url) and file_url.startswith(URL_PREFIXES):
-		response = requests.get(frappe.local.uploaded_file_url)
-	...
+	if not is_local_file_url(file_url):           # no scheme, no netloc, /files/ or /private/files/
+		raise RemoteGenericodeUrlNotAllowedError
+	file_doc = frappe.get_doc("File", {"file_url": file_url})
+	file_doc.check_permission("read")
+	return file_doc.get_content(encodings=()), file_name
```

**Restrict who sets the URL — GHSA-6qcc-cw7f-328g.** Currency Exchange Settings DocPerm. Fix:
[frappe/erpnext#55755](https://github.com/frappe/erpnext/pull/55755): only System Manager can now
write `api_endpoint`. The fetch itself is unchanged.

**PDF rendering — GHSA-mggg-hmjm-j6c2.** `frappe/utils/print_format.py`, `report_to_pdf`. Fix:
[frappe/frappe#36674](https://github.com/frappe/frappe/pull/36674).

```diff
-	frappe.local.response.filecontent = get_pdf(html, {"orientation": orientation})
+	frappe.local.response.filecontent = get_pdf(html, {
+		"orientation": orientation,
+		"proxy": "http://0.0.0.0:0",
+		"bypass-proxy-for": urlparse(frappe.utils.get_url(allow_header_override=False)).hostname,
+		"load-error-handling": "ignore",
+	})
```

**Renderer options from the HTML — GHSA-pj59-9hv9-rmrv.** `frappe/utils/pdf.py`. Fix:
[frappe/frappe#38791](https://github.com/frappe/frappe/pull/38791).

```python
class FrappePDFKit(OriginalPDFKit):
	def _find_options_in_meta(self, content):
		return {}          # ignore <meta name="pdfkit-..."> options embedded in the HTML
```

## XXE — GHSA-mhm9-75w7-423r

`erpnext/edi/doctype/code_list/code_list_import.py`. Fix:
[frappe/erpnext#53302](https://github.com/frappe/erpnext/pull/53302).

```diff
-	parser = etree.XMLParser(remove_blank_text=True)
+	parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False,
+		load_dtd=False, no_network=True)
 	root = etree.fromstring(content, parser=parser)
```

## Open redirect

**Login — GHSA-7g27-q225-j894, then GHSA-j9jr-qrpj-g855.** `frappe/www/login.py`,
`sanitize_redirect`. The first fix ([#26304](https://github.com/frappe/frappe/pull/26304)) allowed
anything without a netloc. The second ([#34017](https://github.com/frappe/frappe/pull/34017))
rebuilds the URL on the request's own host.

```diff
-	if not parsed_redirect.netloc:
-		return redirect
-	if parsed_request_host.netloc == parsed_redirect.netloc:
-		return redirect
-	return None
+	output = parsed_redirect._replace(netloc=parsed_request_host.netloc,
+		scheme=parsed_request_host.scheme)
+	if parsed_redirect.netloc:
+		output = output._replace(path="/app" if parsed_request_host.netloc != parsed_redirect.netloc
+			else parsed_redirect.path)
+	return output.geturl()
```

**Sign-up — GHSA-7m8v-g2pr-h2f7.** `user.sign_up` stores `sanitize_redirect(redirect_to)`
([#35443](https://github.com/frappe/frappe/pull/35443)).

**OAuth state — GHSA-78c5-55xg-jm7m.** `frappe/utils/oauth.py`. Fix:
[frappe/frappe#40962](https://github.com/frappe/frappe/pull/40962).

```diff
-	state = {"site": get_url(), "token": frappe.generate_hash(), "redirect_to": redirect_to}
-	data = {..., "state": base64.b64encode(json.dumps(state).encode())}
+	state = create_oauth_state(redirect_to)       # random token -> cache, 600 s
+	data = {..., "state": state}
 ...
-	state = json.loads(base64.b64decode(state)); redirect_to = state.get("redirect_to")
+	redirect_to = consume_oauth_state(state)      # get + delete; None -> refused
```
