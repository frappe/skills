---
id: A33
area: customization
---
# A33 — Register per-company setup DocTypes in `company_data_to_be_ignored`

**Why:** Transaction Deletion Record deletes every document that links to a company. It reaches
the app's settings, mappings, and registrations too. The user clears test transactions and loses
the app's configuration with them.

**Applies to:** an app that stores per-company configuration in ERPNext.

## Bad

```python
# my_app/hooks.py
app_name = "my_app"
```

The app ships `Tax Registration` and `Regional Settings`, both with a `company` Link field and
neither in any hook.

## Good

```python
# my_app/hooks.py
company_data_to_be_ignored = ["Tax Registration", "Regional Settings"]
```

## Find

- List the app's DocTypes that have a `company` Link field:
  `rg -l '"fieldtype": "Link".*"options": "Company"' --glob '**/doctype/**/*.json'`.
- `rg -n 'company_data_to_be_ignored' hooks.py`.
- A DocType in the first list and not in the second, whose name reads as setup rather than as a
  transaction, is the finding.

## Confirm

`transaction_deletion_record.py` extends its ignore list with
`frappe.get_hooks("company_data_to_be_ignored")`
(`erpnext/setup/doctype/transaction_deletion_record/transaction_deletion_record.py`). The hook
merges across apps.

A submittable DocType that records a business event is a transaction. It should be deleted with
the company data and is not a finding.

A DocType with a `company` field that holds a rate, a mapping, an account setting, a series, or a
registration number is setup. It belongs in the hook.

A Single DocType has no company link and is not affected.
