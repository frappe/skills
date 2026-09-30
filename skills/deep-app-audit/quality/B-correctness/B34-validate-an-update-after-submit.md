---
id: B34
area: correctness
mechanism: M11
---
# B34 — Validate an update after submit, and do not allow one on a field with ledger meaning

**Why:** A submitted document is a signed record. A field marked "Allow on Submit" can be
changed after that signature, and the change does not re-run `validate`. It runs
`before_update_after_submit` and `on_update_after_submit`, and nothing else. A rate, a quantity,
a party, a posting date or an account changed this way leaves the ledger on the old value
forever.

## Bad

```python
# my_app/my_app/doctype/haulage_note/haulage_note.json
{ "fieldname": "rate", "fieldtype": "Currency", "allow_on_submit": 1 }
# the controller has validate() and on_submit() only
```

## Good

```python
# allow_on_submit stays on remarks and on the internal reference only
class HaulageNote(Document):
    def on_update_after_submit(self):
        self.validate_reference_format()
        if self.has_value_changed("customer_reference"):
            self.notify_customer()
```

## Find

- `rg -n '"allow_on_submit": 1' -B 6 --type json` in the app. Read the `fieldname` above each
  hit. A money, quantity, rate, tax, party, company, date, warehouse, item, account or currency
  field is a finding.
- `rg -n 'def on_update_after_submit|def before_update_after_submit' --type py`. A doctype with
  `allow_on_submit` fields and neither method runs no check on the change.
- `rg -n 'def validate' -A 30 --type py` for a check that must also run after submit but is
  called only from `validate`.
- Property Setter records that set `allow_on_submit` on a standard field of a doctype the app
  does not own.

## Confirm

A remark, an internal reference, a print flag and a status that a standard updater owns are the
intended use. `doc.has_value_changed(fieldname)` and `doc.get_doc_before_save()` give the old
value inside the handler. The framework blocks a change to any other field with
`UpdateAfterSubmitError`, so the risk comes only from fields the app or a Property Setter
marked. Setting the property on a standard field belongs to the customization rules; the
missing validation is this rule.
