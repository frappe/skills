# Fix file, path and URL handling in a Frappe app

**A path, a URL and a redirect target from the request are all instructions to the server.** The
strongest fix removes the capability (accept a File record, not a URL). The next confines it
(resolve, then require containment or a fixed host). The weakest validates the string. Prefer them in
that order, and reuse frappe's helper for each — they exist and they handle cases a hand-written check
misses.

## Steps

### 1. Classify the sink and apply its fix

**Caller-supplied `file_url` or file name** — resolve through frappe's own authorization:

```python
from frappe.core.doctype.file.utils import find_file_by_url

file = find_file_by_url(file_url)        # None unless the caller may download it
if not file:
	raise frappe.PermissionError
content = file.get_content()             # path containment is checked inside
```

One `file_url` maps to many File rows, one per attachment. `find_file_by_url` tries them all, while
`frappe.get_doc("File", {"file_url": url})` picks one arbitrarily and wrongly refuses users. Check the
type after resolving (`file.file_type != "CSV"` → refuse). Where the endpoint belongs to an importer
doctype, also `check_permission()` on the importer document: the file check guards the resource, the
doctype check guards the form. **Attaching is a write**: require `write` on the target document and
`read` on every File attached.

**A path built from input** — resolve both sides, then require containment:

```python
from frappe.core.doctype.file.utils import check_path_safety

base = frappe.get_site_path("private", "backups")
target = frappe.get_site_path("private", "backups", user_part)
if not check_path_safety(base_path=base, requested_path=target):   # realpath + commonpath + log
	frappe.throw(_("Invalid path"), frappe.PermissionError)
```

`pathlib` form: `p = (base / user).resolve(); if not p.is_relative_to(base) or not p.is_file(): raise NotFound`.
`startswith(base)` is not containment (`/files_evil` starts with `/files`). Use `commonpath`,
`is_relative_to`, or `startswith(base + os.sep)`. Use `realpath` on **both** sides if anything under the
base can be a symlink. URL-decode before checking. Allow-list the prefix and return nothing otherwise.
Check at **read time** too — a File row can change after it was validated. Write uploads to
`get_files_path(get_safe_file_name(name))`. `frappe.utils.get_files_path` is a
join with no containment check.

**An outbound request to a caller-influenced URL (SSRF):**

1. Best: stop accepting a URL from the caller — accept an uploaded File, or move remote fetching to a
   non-whitelisted backend function.
2. Or restrict who can set it: if the URL lives in a settings field, limit write on that doctype to
   System Manager (who can already run code) — and record that the sink is unchanged.
3. Or confine the request: `frappe.utils.safe_exec.make_safe_get_request(url, timeout=(5, 30))`, which
   on current frappe requires a global address, re-checks **every redirect hop** and **the connected
   peer IP**, ignores environment proxies and sets a timeout. **Read it in your bench**: older majors
   resolve the name once and then follow redirects unchecked. Where that is the case, pass
   `allow_redirects=False` and loop the hops yourself, validating each (as `File.get_web_image` does).

`frappe.utils.validate_url` is a syntax check — it accepts `http://127.0.0.1/`. A one-time resolve
check is beaten by DNS rebinding and redirects.

**HTML rendered to PDF** is an HTTP client too: every `<img>`, `<iframe>` and `<link>` is fetched.
Render caller-influenced HTML with `"proxy": "http://0.0.0.0:0"`, `"bypass-proxy-for": <site host>`
and `"load-error-handling": "ignore"`, and take renderer options from code only — current frappe
ignores `<meta name="pdfkit-…">` tags in the HTML.

**XML parsing** — `defusedxml` is not a frappe dependency, and lxml's defaults resolve entities. On
**every** parser:

```python
parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False, load_dtd=False, no_network=True)
root = etree.fromstring(content, parser=parser)
```

Catch `etree.XMLSyntaxError` and return a fixed message (parser errors echo file content), and escape
parsed values you show back.

**Redirects** — pass every caller-supplied redirect through
`frappe.www.login.sanitize_redirect(url)`, which rebuilds the URL on the request's own host. Testing
"is it relative?" misses `/\evil.com`, `https:evil.com` and `javascript:`. In OAuth flows keep
`redirect_to` server-side and send a random single-use `state`
(`frappe.utils.oauth.create_oauth_state` / `consume_oauth_state`). Build emailed links with
`get_url(path, allow_header_override=False)`.

**Uploads** — serve user markup as a download, from your origin. Private `.svg`, `.html`, `.xml` and
similar are sent as attachments. Public `/files/` are not covered by that. Reject SVG, force download,
or sanitise with `frappe.utils.html_utils.sanitize_svg` where your frappe has it. Image optimisation
does not sanitise SVG. The guest mimetype allow-list does not apply to desk users. Set
`allowed_file_extensions` if desk uploads must be limited. Escape stored image URLs where rendered.

**CSV / spreadsheet export** — write through frappe's exporters (`frappe.utils.csvutils.UnicodeWriter`,
`frappe.desk.utils.get_csv_bytes`, the XLSX writer), which neutralise values starting with
`= + - @ \t \r` (`escape_formula_injection`) and reverse it on import. A raw `csv.writer` does not.

**Archives** — before reading anything, sum the declared member sizes against a limit. Then count the
bytes actually read, because declared sizes lie. Take `os.path.basename()` of member names (zip-slip).
Skip directories, `__MACOSX/` and dotfiles. Frappe's `File.unzip` is the model.

Done when: every caller-influenced path, URL, redirect, file, XML document, archive and export value in
the endpoint passes through one of the fixes above.

### 2. Verify

Run each payload in [payloads.md](file-and-url-handling/payloads.md) as Guest, a Website User, the narrowest
desk role that reaches the endpoint, and the legitimate role (which must still work). Use a private
file owned by Administrator and attached to a document the caller cannot read. For SSRF, watch a
listener you control — a blind SSRF returns nothing. Start with the known-positive control
([verify.md](../verify.md)): every payload must reach the
sink on the pre-fix code.

Done when, on every release line: every payload reached the sink before and is refused after, the
refusal is a 403 or a fixed message (the parser's or HTTP client's exception text stays server-side),
and the legitimate call is unchanged.

## References

- [payloads.md](file-and-url-handling/payloads.md) — per-class payloads, including the redirect bypass table.
- Shipping, backports and the public PR: [the security workflow](../workflow.md).
