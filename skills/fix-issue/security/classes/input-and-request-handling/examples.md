# Published request-handling fixes

## State-changing endpoints reachable over GET — GHSA-cprh-gp85-wxvq

Fix: [frappe/frappe#32984](https://github.com/frappe/frappe/pull/32984).

```diff
-@frappe.whitelist()
+@frappe.whitelist(methods=["POST"])
 def execute_code(doc):                       # frappe/desk/doctype/system_console/system_console.py
-@frappe.whitelist()
+@frappe.whitelist(methods=["POST", "PUT"])
 def savedocs(doc, action):                   # frappe/desk/form/save.py
-@frappe.whitelist()
+@frappe.whitelist(methods=["POST", "DELETE"])
 def delete_items():                          # frappe/desk/reportview.py
```

`execute_code` commits itself, so the GET rollback did not protect it.

## OAuth consent: POST-only approval and a token in the page — GHSA-2ph8-x773-8p2x

`frappe/integrations/oauth2.py`. Fix: [frappe/frappe#40073](https://github.com/frappe/frappe/pull/40073).

```diff
-@frappe.whitelist()
+@frappe.whitelist(methods=["POST"])
 def approve(*args, **kwargs):
 ...
-	unrevoked_tokens = frappe.db.exists("OAuth Bearer Token", {"status": "Active", "user": frappe.session.user})
+	unrevoked_tokens = frappe.db.exists("OAuth Bearer Token",
+		{"status": "Active", "user": frappe.session.user, "client": frappe.flags.oauth_credentials["client_id"]})
 ...
+		"csrf_token": get_csrf_token(),
```

Auto-approval was also scoped to the requesting client, not any active token of the user.

## The payload chose the DocType — GHSA-x635-wr4c-7345

`erpnext/crm/frappe_crm_api.py`, `create_customer`. Fix:
[frappe/erpnext#55486](https://github.com/frappe/erpnext/pull/55486).

```diff
+CUSTOMER_ALLOWED_FIELDS = {"customer_name", "customer_group", "customer_type", "territory", ...}
 @frappe.whitelist()
 def create_customer(customer_data: dict | None = None):
+	validate_frappe_crm_sync()          # feature enabled, and the caller is an allowed user
 ...
-	customer = frappe.get_doc({"doctype": "Customer", **customer_data}).insert(ignore_permissions=True)
+	customer = frappe.new_doc("Customer")
+	for field in CUSTOMER_ALLOWED_FIELDS:
+		if customer_data.get(field) is not None:
+			customer.set(field, customer_data.get(field))
+	customer.insert(ignore_permissions=True)
```

## A bypass flag taken from the request — GHSA-94v6-784v-24q5

`erpnext/accounts/utils.py`, `add_ac`. Fix: [frappe/erpnext#55665](https://github.com/frappe/erpnext/pull/55665).

```diff
 	if not args:
 		args = frappe.local.form_dict
+	args.pop("ignore_permissions", None)
+	frappe.has_permission("Account", "create", throw=True)
 	...
 	ac = frappe.new_doc("Account")
-	if args.get("ignore_permissions"):
-		ac.flags.ignore_permissions = True
-		args.pop("ignore_permissions")
 	ac.update(args)
```

## A limit the UI applied and the server did not — GHSA-5h4c-9p23-4c3m

`frappe/share.py`. Fix: [frappe/frappe#35497](https://github.com/frappe/frappe/pull/35497). The share
dialog only offered permissions the sharer held. The server accepted any.

```diff
-def check_share_permission(doctype, name):
+def check_share_permission(doctype, name, permissions=None, custom_perms=None):
 	if not frappe.has_permission(doctype, ptype="share", doc=name):
 		frappe.throw(...)
+	if not permissions:
+		return
+	restricted_permissions = ["read", "write", "submit"] + custom_perm_types
+	doc = frappe.get_doc(doctype, name)
+	for ptype in restricted_permissions:
+		if cint(permissions.get(ptype)) and not frappe.has_permission(doctype, ptype, doc=doc):
+			frappe.throw(_("You cannot share `{0}` on {1} `{2}` ..."), frappe.PermissionError)
```
