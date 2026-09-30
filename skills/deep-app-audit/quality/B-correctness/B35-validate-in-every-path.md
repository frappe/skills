---
id: B35
area: correctness
---
# B35 — A validation must run in every path that can change the data it protects

**Why:** A rule that lives in one entry point is not a rule. The REST API, a background job, a
data import, a document mapper, an update after submit and a rename each reach the data by a
different path. A check that only runs in `validate` is bypassed by an update after submit and
by a direct database write. A check that only runs in the browser is bypassed by every caller
that is not a browser.

## Bad

```python
class Consignment(Document):
    def validate(self):
        if flt(self.declared_weight) > flt(self.max_weight):
            frappe.throw(_("Declared weight is above the limit"))
    # declared_weight has allow_on_submit: 1 and there is no on_update_after_submit
```

## Good

```python
class Consignment(Document):
    def validate(self):
        self.validate_weight()

    def on_update_after_submit(self):
        self.validate_weight()

    def validate_weight(self):
        if flt(self.declared_weight) > flt(self.max_weight):
            frappe.throw(_("Declared weight is above the limit"))
```

## Find

- `rg -n 'def validate_\w+' --type py` in the app, then list the call sites of each. A check
  called from one lifecycle method only is a candidate.
- `rg -n 'frappe\.validated\s*=\s*false|frappe\.throw' --type js` in app JS and Client Script
  records. Every such rule needs a server-side twin.
- `rg -n 'ignore_validate|ignore_mandatory|ignore_links|ignore_permissions' --type py` in the
  app. Each one switches a check off for that path.
- `rg -n 'get_mapped_doc\(' --type py`. A mapper builds a document without running the source
  document's checks.

## Confirm

A check that is deliberately relaxed in a state, such as a draft, is correct when the guard
names that state, for example `if self.docstatus == 1`. The finding is a path with no check at
all. A client-side check is a usability feature and never an enforcement point: the standard
form is the only place it runs. A check inside a Server Script of type DocType Event does run
for API callers, but not during install and migrate
(`source:frappe/core/doctype/server_script/server_script_utils.py:run_server_script_for_doc_event`).
