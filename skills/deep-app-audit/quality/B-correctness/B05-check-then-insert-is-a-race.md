---
id: B05
area: correctness
---
# B05 — Check then insert is a race. Enforce uniqueness in the database

**Why:** MariaDB runs at repeatable read. A transaction sees the snapshot taken when it
started and never sees a row another transaction committed after that. Two workers both find
no row and both insert. The window is the whole transaction, not the two lines of code, so the
race is common on a slow request. The result is a duplicate master, a double payment, or a
second ledger voucher for one event.

## Bad

```python
@frappe.whitelist()
def register_device(serial_no, customer):
    if not frappe.db.exists("Device", {"serial_no": serial_no}):
        frappe.get_doc({
            "doctype": "Device",
            "serial_no": serial_no,
            "customer": customer,
        }).insert()
```

## Good

```python
# Device.serial_no carries "unique": 1 in the DocType JSON.
@frappe.whitelist()
def register_device(serial_no, customer):
    try:
        frappe.get_doc({
            "doctype": "Device",
            "serial_no": serial_no,
            "customer": customer,
        }).insert()
    except frappe.UniqueValidationError:
        return frappe.db.get_value("Device", {"serial_no": serial_no}, "name")
```

## Find

- `rg -n 'if not frappe\.db\.exists' -A 8 --type py` in the app. Keep every hit with an
  `insert`, a `save` or a `frappe.db.sql` insert in the block.
- `rg -n 'frappe\.db\.count\(' -A 6 --type py` where the count decides whether to write.
- `rg -n 'get_value\(' -A 8 --type py` where an empty result leads to an insert.
- The DocType JSON of the target: check for `"unique": 1` on the field the check reads.

## Confirm

A check that only skips work, and where a duplicate row is harmless, is not a finding. A check
inside a `frappe.utils.synchronization.filelock`, or after a
`frappe.db.get_value(..., for_update=True)` on a row that every writer locks first, closes the
window. A unique index is the strongest form and works across processes and sites. When the
rule spans more than one column, use a composite unique index or B06.
