# Published missing-authorization fixes, by shape

All are published GitHub Security Advisories with merged, released fixes.

## `get_doc` on a request name → `check_permission` — GHSA-pr7v-95jp-gwwv

`get_contract_template`. Fix: [frappe/erpnext#58621](https://github.com/frappe/erpnext/pull/58621).

```diff
 	contract_template = frappe.get_doc("Contract Template", template_name)
+	contract_template.check_permission()
```

The same shape fixed `lead.get_lead_details` (GHSA-gq9h-847p-h692,
[#56272](https://github.com/frappe/erpnext/pull/56272)).

## `get_all` → `get_list` — GHSA-g8r3-82j6-wp48

`crm/doctype/prospect/prospect.py`, `get_opportunities`. Fix:
[frappe/erpnext#56463](https://github.com/frappe/erpnext/pull/56463).

```diff
 def get_opportunities(prospect: str):
-	return frappe.get_all(
+	return frappe.get_list(
 		"Opportunity",
 		filters={"opportunity_from": "Prospect", "party_name": prospect},
```

## Two steps for a child table — GHSA-9vph-hqmm-g7hq

`projects/doctype/timesheet/timesheet.py`, `get_timesheet`, a link query over `Timesheet Detail`.
Fix: [frappe/erpnext#58267](https://github.com/frappe/erpnext/pull/58267).

```python
allowed_timesheets = frappe.get_list("Timesheet", pluck="name")   # parent, permission-checked
if not allowed_timesheets:
	return []
query = (
	frappe.qb.from_(tsd)
	.inner_join(ts).on(tsd.parent == ts.name)
	.select(tsd.parent).distinct()
	.where(... & tsd.parent.isin(allowed_timesheets))             # child bounded by parent names
)
```

## The guarded resource is not the endpoint's DocType — GHSA-726x-68g4-fj9v

`accounts/doctype/invoice_discounting/invoice_discounting.py`, `get_invoices`. Fix:
[frappe/erpnext#58975](https://github.com/frappe/erpnext/pull/58975). One PR carries the guard on the
resource (Company), the caller change (the JS now sends `company`), and the DocPerm change with its
`modified` bump.

```diff
 	filters = frappe._dict(frappe.parse_json(filters))
+	if not filters.get("company"):
+		frappe.throw(_("Please set company on the Document before requesting for invoices."))
+	frappe.has_permission("Company", doc=filters.get("company"), throw=True)
+	frappe.has_permission("Invoice Discounting", throw=True)
```

## The importer form boundary — GHSA-jfwr-g9v2-57c9

Bank Statement Import, `get_preview_from_template`. Fix:
[frappe/erpnext#58221](https://github.com/frappe/erpnext/pull/58221). The same PR added
`check_permission("write")` to the mutators and `methods=["POST"]`.

```diff
-	return frappe.get_doc("Bank Statement Import", data_import).get_preview_from_template(
-		import_file, google_sheets_url)
+	bsi = frappe.get_doc("Bank Statement Import", data_import)
+	bsi.check_permission()
+	return bsi.get_preview_from_template(import_file, google_sheets_url)
```

The file itself is a separate boundary: resolve a caller-supplied file URL with `find_file_by_url`
and refuse on `None`.

## A mutating whitelisted function → Document method with a write check — GHSA-pg3r-7236-pg74

Purchase Invoice `block_invoice`. Fix: [frappe/erpnext#57825](https://github.com/frappe/erpnext/pull/57825).

```python
# before: module-level, no check
@frappe.whitelist()
def block_invoice(name, release_date, hold_comment=None):
	if frappe.db.exists("Purchase Invoice", name):
		frappe.get_lazy_doc("Purchase Invoice", name).block_invoice(hold_comment, release_date)

# after: run_doc_method checks only read, and db_set checks nothing
@frappe.whitelist(methods=["POST"])
def block_invoice(self, hold_comment=None, release_date=None):
	self.check_permission("write")
	...
	self.db_set({"on_hold": 1, "hold_comment": cstr(hold_comment), "release_date": release_date})
```

## Removing the endpoint — GHSA-cgxw-2996-9vj3

`crm/doctype/utils.py`, `get_last_interaction`. Fix:
[frappe/erpnext#58214](https://github.com/frappe/erpnext/pull/58214) deleted an unused whitelisted
function that returned `Communication.content` for any Contact or Lead. A guard probe reports a
removal as "unfixed" forever. The test is that the function is absent at the ref.

## Removing an `ignore_permissions` argument — GHSA-wwgm-3pv3-gmqh

`accounts/party.py`, `get_party_details`. Fix:
[frappe/erpnext#55491](https://github.com/frappe/erpnext/pull/55491).

```diff
 	doctype: str | None = None,
-	ignore_permissions: bool | None = False,
 	fetch_payment_terms_template: bool = True,
 ...
-		ignore_permissions,
+		False,
```

An inner helper still has an `ignore_permissions` parameter after the fix, so a token grep reports it
unfixed. What matters is that the caller can no longer set it.

## The guard sits in configuration — GHSA-wrh5-p77r-jpvq (frappe)

`core/doctype/sms_settings/sms_settings.py`, `send_sms`: a roles table on SMS Settings, checked at the
endpoint.

```python
def check_sms_permission():
	user_roles = set(frappe.get_roles())
	if "System Manager" in user_roles:
		return
	allowed_roles = {d.role for d in frappe.get_single("SMS Settings").get("allowed_roles") if d.role}
	if not user_roles & allowed_roles:
		frappe.throw(_("You are not permitted to send SMS"), frappe.PermissionError)

@frappe.whitelist()
def send_sms(receiver_list, msg, sender_name="", success_msg=True):
	check_sms_permission()
	return _send_sms(receiver_list, msg, sender_name, success_msg)
```

To verify a fix of this shape, read the configuration DocType, not the sink.
