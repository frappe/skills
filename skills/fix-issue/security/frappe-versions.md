# Write the fix for the line's frappe

Each release line of an app runs on one frappe major. A fix calls frappe APIs, and those APIs
differ between majors: a helper exists on one and is missing on another, a keyword is accepted on
one and rejected on another, a check is strict on one and loose on another. A fix written against
the wrong major either fails to import or, worse, imports and does not guard.

So each branch unit writes its fix against **its own line's frappe**, in its own bench.

## Steps

### 1. Name the frappe branch

Read the range from the app's `pyproject.toml` at the line:

```bash
git -C <bench>/apps/<app> show "upstream/<line>:pyproject.toml" | grep -A2 'frappe-dependencies'
```

The range names the frappe major. Pair the app's `version-N` or `version-N-hotfix` line with
frappe's `version-N-hotfix`, and `develop` with frappe's `develop`. Confirm that the bench's
`apps/frappe` is on that branch: `git -C <bench>/apps/frappe rev-parse --abbrev-ref HEAD`.

Done when: the unit has written down its frappe branch, and the bench's frappe checkout matches it.

### 2. Read every frappe API the fix calls, at that branch

For each frappe function, keyword or helper the fix uses:

```bash
git -C <bench>/apps/frappe grep -n "def <name>" upstream/<frappe-branch> -- frappe
git -C <bench>/apps/frappe show "upstream/<frappe-branch>:<file>" | sed -n '/def <name>/,/^def /p'
```

Read the body, not only the name. A function can exist on two majors with different checks inside
it. For behaviour that lives in an installed dependency rather than in frappe, read the bench's
environment. For example, query-builder identifier quoting depends on the installed `pypika`:

```bash
<bench>/env/bin/python -c "import pypika.utils, inspect; print(inspect.getsource(pypika.utils.format_quotes))"
```

Done when: every frappe API in the fix has been read at the line's frappe branch, and each one
exists and does what the fix needs.

### 3. Write with what that frappe has

Where an API is missing or weaker on this line, use the line's equivalent from the table below.
Keep the guard's shape and names the same as on the other lines, and change only the call that
the major forces. Record each difference in the branch ledger with its reason.

Done when: the fix imports and runs on the line's bench, and every difference from the other lines
is in the ledger.

### 4. Test on the line's own bench

The two-site regression ([verify.md](verify.md)) runs on the line's bench, so it runs on the line's
frappe. A pass on one major says nothing about another.

Done when: the two-site regression has passed on this line's bench.

## Known differences between frappe majors

Measured in October 2026 on frappe `develop`, `version-16-hotfix` and `version-15-hotfix`.
Backports move behaviour between majors, so step 2 still applies to every row.

| API or behaviour | develop | version-16 | version-15 | On a line without it |
| --- | --- | --- | --- | --- |
| `frappe.throw_permission_error()` (for a docname the method looked up itself) | yes | yes | only in `frappe.handler` | `frappe.throw(_("Not permitted"), frappe.PermissionError)` |
| `frappe.qb.get_query(..., ignore_permissions=False)` | yes | yes | no permission mode | `frappe.get_list`, or an explicit `frappe.has_permission(..., doc=)` |
| `get_query` validates caller-supplied `fields` and `filters` keys | yes | yes | filter keys only with `validate_filters=True`, fields weakly | allow-list against `frappe.get_meta(dt).get_valid_columns()` |
| `get_list` DocType check on `select` (`check_select_permission`) | in `database/query.py` | in `database/query.py` | in `model/db_query.py` | read the permission path in that file before relying on it |
| `frappe.has_permission(..., throw=True)` forwards logging as | `print_logs` | `print_logs` | `raise_exception` | same effect: the refusal can name a linked value |
| `make_safe_request` / `get_safe_request_session` (re-check each redirect hop and the peer IP) | yes | yes | no | `allow_redirects=False`, and validate every hop yourself |
| `frappe.utils.data.validate_egress_url` | yes | yes | no | resolve the host and reject non-global addresses yourself |
| `frappe.utils.html_utils.sanitize_svg` | yes | no | no | reject SVG uploads, or force them to download |
| `@frappe.whitelist(force_types=...)` | yes | no | no | check argument types in the body |
| `@rate_limit(user_based=..., endpoint=...)` | yes | no | no | `key=` or `ip_based=` |
| Python | 3.14 | 3.14 | 3.10 to 3.14 | read `requires-python` in frappe's `pyproject.toml` |
| Node | 24 or later | 24 or later | 18 or later | read `engines` in frappe's `package.json` |
