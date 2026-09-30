---
id: M57
---
# M57 — App-level data and log settings

**What:** A group of hooks declares app-level settings rather than behaviour.
`default_log_clearing_doctypes` maps a log DocType to its default retention in days and seeds
Log Settings. `user_data_fields` lists the DocTypes that hold personal data of a user, for the
data download and delete requests. `get_site_info` adds fields to the site information payload.
`export_python_type_annotations`, `expose_discovery_source` and
`require_type_annotated_api_methods` are booleans that change developer-facing behaviour.
`ignore_translatable_strings_from` excludes paths from translation extraction, and
`translations/<lang>.csv` in the app supplies the app's own translations.

**Guards:** `add_default_logtypes` adds a row only when the DocType exists and only when it
supports log clearing, which means the controller provides a `clear_old_logs` method. The
retention value is read with `[-1]`, so the last app on the bench sets the days for a DocType
two apps both declare. A DocType already present in Log Settings is not touched, so the hook is
a default and not a policy. The boolean hooks are read with `any()`, so one app turns the
behaviour on for the whole bench. `get_site_info` handlers each update the same dict, so a
handler that reuses a key overwrites another app's value.

## Good use

A log DocType the app ships declares its own retention and provides the method that makes
clearing possible.

```python
# hooks.py
default_log_clearing_doctypes = {"Permit Sync Log": 30}
```

```python
# my_app/my_app/doctype/permit_sync_log/permit_sync_log.py
class PermitSyncLog(Document):
	@staticmethod
	def clear_old_logs(days=30):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Permit Sync Log")
		frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))
```

Without that method the hook adds nothing and the table grows without a bound.

`user_data_fields` names the DocTypes that hold data of one user, with the field that links to
that user, so a data request returns the app's data too:

```python
# hooks.py
user_data_fields = [{"doctype": "Permit Application", "filter_by": "applicant_email"}]
```

`get_site_info` handlers write under a key named after the app, and they return a dict of small,
flat values.

Translations belong in `<app>/translations/<lang>.csv`, generated from the source strings. Every
string a user reads is marked in the code, so the extraction finds it.

## Rules

- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve.
- A24 — A `hooks.py` value is static data, computed once per process.
