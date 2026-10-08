# Published authentication and disclosure fixes

## A signed link used to impersonate — GHSA-cgwf-xgph-hxgm

`frappe/workflow/doctype/workflow_action/workflow_action.py`, `confirm_action`. Fix:
[frappe/frappe#40489](https://github.com/frappe/frappe/pull/40489).

```diff
-@frappe.whitelist(allow_guest=True)
+@frappe.whitelist()
 def confirm_action(doctype: str, docname: str | int, user: str, action: str):
 	if not verify_request():
 		return
-	logged_in_user = frappe.session.user
-	if logged_in_user == "Guest" and user:
-		# to allow user to apply action without login
-		frappe.set_user(user)
 	doc = frappe.get_doc(doctype, docname)
```

## A check enforced on some login paths only — GHSA-h9jq-7pgf-hw8q

`frappe/auth.py`, `validate_auth`. Fix: [frappe/frappe#41883](https://github.com/frappe/frappe/pull/41883).
The IP allow-list now applies to API key, OAuth and `auth_hooks` logins too.

```diff
 def validate_auth():
 	authorization_header = frappe.get_request_header("Authorization", "").split(" ")
+	user_before_auth = frappe.session.user
 	...
+	if frappe.session.user != user_before_auth and frappe.session.user not in ("", "Guest"):
+		validate_ip_address(frappe.session.user)
```

## Token links built from the Host header — GHSA-p284-r7rh-wq7j, GHSA-3w78-3cj3-p949

Fixes: [frappe/frappe#31522](https://github.com/frappe/frappe/pull/31522) (password reset) and
[frappe/frappe#39331](https://github.com/frappe/frappe/pull/39331) (one-time login).

```diff
-def get_url(uri: str | None = None, full_address: bool = False) -> str:
+def get_url(uri=None, full_address=False, allow_header_override: bool = True) -> str:
 ...
-		if request_host_name:
+		if request_host_name and allow_header_override:
 			host_name = request_host_name
 # callers:
-	link = get_url(url)
+	link = get_url(url, allow_header_override=False)
```

## A derivable access key — GHSA-7xv4-ggpj-g48q

Fix: [frappe/frappe#17021](https://github.com/frappe/frappe/pull/17021). The print-view key was
`sha224(creation timestamp)`, and other endpoints exposed the timestamp. It became a random, stored,
expiring `Document Share Key`.

```python
def get_signature(self):   # before
	return hashlib.sha224(get_datetime_str(self.creation).encode()).hexdigest()

# after: a Document Share Key row whose before_insert sets
#   self.key = frappe.generate_hash(length=randrange(25, 35))
# printview looks the key up, and raises LinkExpired once expires_on has passed.
```

## Enumeration through password reset — GHSA-3vqc-c545-w7jg

`frappe/core/doctype/user/user.py`, `reset_password`. Fix:
[frappe/frappe#38588](https://github.com/frappe/frappe/pull/38588).

```diff
 	try:
-		user: User = frappe.get_doc("User", user)
-		if user.name == "Administrator":
-			return "not allowed"
-		if not user.enabled:
-			return "disabled"
+		user_doc: User = frappe.get_doc("User", user)
+		if user_doc.name != "Administrator" and user_doc.enabled:
+			user_doc.validate_reset_password()
+			user_doc.reset_password(send_email=True)
 	except frappe.DoesNotExistError:
-		frappe.local.response["http_status_code"] = 404
 		frappe.clear_messages()
-		return "not found"
+	return frappe.msgprint(msg=_("If an account with this email exists, password reset instructions have been sent."), ...)
```

## Enumeration through a record-creating guest form — GHSA-c2xv-c53h-qvr5

Personal Data Deletion Request. Fix: [frappe/frappe#40787](https://github.com/frappe/frappe/pull/40787).

```python
def as_dict(self, *args, **kwargs):
	d = super().as_dict(*args, **kwargs)
	d.pop("user_name", None)
	return d

def insert(self, *args, **kwargs):
	if not frappe.db.exists("User", self.user):
		self.name = frappe.generate_hash(length=10)   # looks like success; nothing is saved
		...
		return self
	return super().insert(*args, **kwargs)
```

## Authorised once, mailed forever — GHSA-wcm9-vvcc-r8pr, GHSA-7vpf-q96h-59x4

`frappe/desk/form/document_follow.py`. Fix (version-15):
[frappe/frappe#40041](https://github.com/frappe/frappe/pull/40041). Permission is re-checked per
recipient at send time, and field permlevel is checked for changelog data.

```diff
 	for document_follow in latest_document_follows:
+		if not frappe.has_permission(document_follow.ref_doctype, "read",
+				doc=document_follow.ref_docname, user=user):
+			frappe.db.delete("Document Follow", {"ref_doctype": ..., "ref_docname": ..., "user": user})
+			continue
 		content = get_message(document_follow.ref_docname, document_follow.ref_doctype, frequency, user)
```

## Secrets in logged tracebacks — GHSA-38fg-mjcm-3hc6

Fixes: [frappe/frappe#19805](https://github.com/frappe/frappe/pull/19805) and
[frappe/frappe#22012](https://github.com/frappe/frappe/pull/22012). Tracebacks written to the error
log mask local variables whose names look like secrets.
