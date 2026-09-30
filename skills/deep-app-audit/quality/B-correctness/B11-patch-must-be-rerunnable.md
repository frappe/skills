---
id: B11
area: correctness
mechanism: M04
---
# B11 — A patch must produce the same result when it runs twice

**Why:** A patch that fails halfway leaves the site part-migrated and blocks `bench migrate`
for every user of that site. The operator then reruns the patch. A patch that is not
re-runnable either fails again on the state it made, or applies its change a second time. A
patch must also tolerate a site where the field, the DocType or the value it expects is
absent.

## Bad

```python
# my_app/patches/v1_0/split_contact_name.py
def execute():
    for row in frappe.get_all("Contact", fields=["name", "full_name"]):
        first, last = row.full_name.split(" ")  # fails on an empty or one-word value
        doc = frappe.get_doc("Contact", row.name)
        doc.first_name = first
        doc.last_name = last
        doc.save()  # one save per row, no bound, no resume point
```

## Good

```python
# my_app/patches/v1_0/split_contact_name.py
from frappe.utils import create_batch

def execute():
    if not frappe.db.has_column("Contact", "full_name"):
        return

    rows = frappe.get_all(
        "Contact",
        filters={"full_name": ("is", "set"), "first_name": ("is", "not set")},
        fields=["name", "full_name"],
    )
    for batch in create_batch(rows, 500):
        updates = {}
        for row in batch:
            first, _, last = (row.full_name or "").partition(" ")
            updates[row.name] = {"first_name": first, "last_name": last}
        frappe.db.bulk_update("Contact", updates)
```

## Find

- `rg -n 'def execute' -A 40 patches/ --type py` in the app. Keep every patch with a write that
  has no filter for the rows it already changed.
- `rg -n 'for .* in frappe\.get_all\(' -A 8 patches/` followed by `get_doc` and `save`. This is
  the per-row shape that times out on a large table.
- `rg -n 'frappe\.get_all\(' patches/` with no `filters` and no `limit`.
- `rg -n 'has_column|has_index|db\.exists\("DocType"|db_type' patches/`. A patch with none of
  these assumes one site state.

## Confirm

A patch whose write is already conditional on the value it sets is re-runnable. A patch that
only calls `frappe.reload_doc` or `rename_field` is re-runnable, because both are no-ops the
second time. `Patch Log` normally stops a second run, but the operator reruns a failed patch on
purpose, and the log dedupes on the patch string alone
(`source:frappe/modules/patch_handler.py:run_all`), so two apps that ship the same
`execute:` line run it once in total. A patch that writes more than 200,000 rows in one action
raises `TooManyWritesError`, so batching is a correctness need, not only a cost need.
