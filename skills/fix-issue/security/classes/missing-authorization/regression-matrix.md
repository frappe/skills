# The regression matrix for a permission fix

A permission fix has two failure modes: it leaves the hole open (the **security** test), or it shuts
out a legitimate user (the **regression** test). A run that only checks the first has tested the hole,
not the fix.

## Identities

Enumerate them from the guard target's DocPerm rows, not from the report's prose.

| # | Identity | Expect | Why it is in the matrix |
|---|---|---|---|
| 1 | A role holding the guard ptype | same data as before | the baseline |
| 2 | Each **loser**: a role with write/create on a calling form | same data as before | the regression test — these are who break at upgrade |
| 3 | A **select-only** role, if one exists | depends on the ptype you chose | catches the silent `get_list` → `select` downgrade |
| 4 | A User Permission-**fenced** user (a role plus a User Permission on a linked record) | own records only | the only identity that tells a doctype-level check from a record-level one |
| 5 | A System User with no roles | refused | the security test |
| 6 | A **Website User** | refused | authenticated, so the whitelist gate never stops them and only your guard does — this is the row that carries real severity |
| 7 | Guest | refused | `frappe.is_whitelisted` refuses Guest before the body unless the method is `allow_guest`, so this row says little about your guard |
| 8 | Administrator | allowed | short-circuits every check — a suite that runs only as Administrator proves nothing |
| 9 | Internal / server callers | unchanged | they call the inner helper, not the endpoint |

## Rules

- **Compare return values.** For at least one entitled identity, capture the return
  value for the same crafted input before and after the fix. A guard that narrows a result set passes
  "no exception" and fails a user. For a `get_list` conversion, confirm it returns the caller's own
  rows — not empty, not everything.
- **Vary the arguments, not only the identities.** Call with and without each optional argument, and
  with malformed names: `{"name": ["like", "%"]}`, `["like", "%"]`, `""`, a missing name.
- **Check what the refusal says.** For a docname the method looked up itself, the `PermissionError`
  text and every `frappe.message_log` entry are the constant refusal. For a caller-supplied
  docname, frappe's message names only what the caller sent.
- **A denial on an entitled identity is a stop, not a note.**
- **Run the matrix on both sites of the two-site regression**, on every release line
  ([verify.md](../../verify.md) step 4).

## Writing it as a test

```python
from contextlib import contextmanager

@contextmanager
def as_user(user):
	previous = frappe.session.user
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(previous)


def test_refuses_unpermitted_user(self):
	with as_user("website-user@example.com"):
		self.assertRaises(frappe.PermissionError, endpoint, name=other_company_record)

def test_entitled_role_unchanged(self):
	with as_user("stock-user@example.com"):
		self.assertEqual(endpoint(name=own_record), EXPECTED)

def test_malformed_name_refused(self):
	for bad in ({"name": ["like", "%"]}, ["like", "%"], ""):
		with as_user("stock-user@example.com"):
			self.assertRaises((frappe.PermissionError, frappe.ValidationError), endpoint, name=bad)
```

Create users with the exact roles and User Permissions the row needs, and clear caches after changing
them (`frappe.clear_cache(user=…)`).
