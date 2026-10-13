# Example of the security path

A full fix in a custom app. It starts the way every security fix starts: the human runs
`/fix-issue` on the report. The security path never starts by itself.

---

## A backport to version-15 in a custom app

The app is an invented custom app, `library_management`, which ships from `main` (frappe 16) and
`version-15` (frappe 15). The flaw is already fixed on `main` by commit `7c41e2a`, from pull request
#212. The human runs `/fix-issue` in the `version-15` bench, so this run fixes `version-15` only.
Output marked *illustrative* shows the shape of what the agent prints for this invented app.

### The human runs

```text
/fix-issue reports/member-loans.md
```

### `SKILL.md` step 1: the brief

The extractor agent reads the report and returns facts only:

> - **Symptom:** a member can see the loan history of every other member.
> - **Effect:** the response lists all loans of `MEM-0042`.
> - **Actor:** Website User with the Library Member role.
> - **Request:** `GET /api/method/library_management.api.get_member_loans?member=MEM-0042`, sent
>   by the member who owns `MEM-0007`.
> - **Gaps:** none.

The brief has an **Effect**, so the agent runs `SKILL.md` steps 2 and 3 with their **Security**
lines, then follows `security/workflow.md`.

### `SKILL.md` step 2: reproduce, as the actor

On `version-15`, the request from the brief, sent as the member who owns `MEM-0007`, returns the
loans of `MEM-0042`. This payload is the known-positive control.

### `SKILL.md` step 3: find the cause

```python
# library_management/api.py
@frappe.whitelist()
def get_member_loans(member: str):
	return frappe.get_all(
		"Library Loan",
		filters={"member": member},
		fields=["name", "book", "issued_on", "returned_on"],
	)
```

> **Location:** `library_management/api.py::get_member_loans` · **Actor:** Website User · **Input:**
> `member` · **Cause:** the sink is `frappe.get_all`, which applies no permissions, on a
> caller-chosen `member`.

### `workflow.md` step 1: pin the branch

> The app checkout is on `version-15`, which runs frappe 15 (`">=15.40.0,<16.0.0"`), and
> `apps/frappe` is on `version-15-hotfix`. Do I fix `version-15`?

The human confirms. The checkout is clean, so the agent cuts the fix branch from the remote head:

```text
$ git -C apps/library_management fetch upstream --tags
$ git -C apps/library_management switch --no-track -c fix/member-loans-access upstream/version-15
Switched to a new branch 'fix/member-loans-access'
```

It migrates its site and builds the assets. The known-positive control works at `4be21c0`, so this
branch has the flaw.

### `workflow.md` step 2: classify

`frappe.get_all` on a caller-supplied filter points to `classes/missing-authorization.md`. Then:

> - **Other half:** `member` reaches only a filter value, so the query has no injection. It arrives
>   as a filter value, so it also gets a type check from `classes/input-and-request-handling.md`.
> - **Sibling sweep:** `grep -rn 'frappe.get_all("Library' library_management/` finds two more
>   whitelisted reads: `get_member_fines`, with the same shape (fix it), and `get_catalogue`, which
>   is public by design (recorded as unreachable).

### `workflow.md` step 3: port, and cross-verify with this branch's APIs

The log names the fix on `main`, and `gh pr list --search "#212 in:title,body" --state all` finds no
backport pull request yet. The agent applies the fix without committing:

```text
$ git cherry-pick -n 7c41e2a
```

It applies cleanly. The agent lists every frappe API the diff calls and reads each one at frappe
`version-15-hotfix`, as `frappe-versions.md` step 2 says:

| API in the diff | At frappe `version-15-hotfix` | Result |
| --- | --- | --- |
| `frappe.get_list("Library Loan", filters=…, fields=…)` | exists, applies role permissions and User Permissions | keep |
| `frappe.bold` | exists, escapes first | keep |
| `frappe.qb.get_query("Library Fine", …, ignore_permissions=False)` | the query engine has no permission mode, and `get_query` takes no `ignore_permissions` argument | **replace** |

*(illustrative)*

The cherry-pick applied and imported, yet `get_member_fines` would raise a `TypeError` on its first
call, for every user. The agent replaces that one call with this branch's equivalent, from the
table in `frappe-versions.md`:

```diff
-	query = frappe.qb.get_query(
-		"Library Fine", fields=["member", {"SUM": "amount", "as": "total"}],
-		group_by="member", ignore_permissions=False,
-	)
-	return query.run(as_dict=True)
+	return frappe.get_list(
+		"Library Fine", fields=["member", "sum(amount) as total"], group_by="member"
+	)
```

`get_member_loans` keeps the shape of the original fix:

```diff
 @frappe.whitelist()
 def get_member_loans(member: str):
-	return frappe.get_all(
+	if not isinstance(member, str) or not member:
+		frappe.throw(_("{0} must be a non-empty string").format(frappe.bold("member")))
+	return frappe.get_list(
 		"Library Loan",
 		filters={"member": member},
 		fields=["name", "book", "issued_on", "returned_on"],
 	)
```

Both files are at the same paths on `version-15`. The agent writes down the one difference:
`get_member_fines` uses `get_list`, because frappe 15's `get_query` has no permission mode.

**Loser set**, from `missing-authorization.md` step 3: `get_list` authorizes on `select`.

```text
roles with write on the calling form (Library Member)   = Librarian, Library Manager
roles with select/read on Library Loan                  = Library Manager, Library Member
losers                                                  = Librarian
```

**DocPerm rows**, from `missing-authorization.md` step 4: the original fix grants `Librarian`
`select` and `read` on `Library Loan` in `library_loan.json`. The agent keeps the rows and sets
`modified` to this branch's current datetime:

```bash
$ python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))"
2026-10-13 10:14:52.381907
```

The Custom DocPerm mirror patch from the original fix comes along unchanged, as
`missing-authorization/docperm-shipping.md` says. The guard, the rows and the patch stay in one
commit.

**Portal callers:** members see their own loans on `www/my-loans.py`. Members hold the app's
`Library Member` role, which has `read` on `Library Loan`, and a User Permission on their own
`Library Member` record. `get_list` applies that User Permission, so each member gets their own
rows. The agent opens the page as a member to confirm it.

### `workflow.md` step 4: test

The agent adds two tests to `test_api.py`, named for the behaviour:
`test_member_sees_only_own_loans` (as the member who owns `MEM-0007`) and
`test_librarian_sees_member_loans` (as a Librarian). The first fails on `upstream/version-15`. Both
pass with the fix.

### `workflow.md` step 5: commit locally, then verify

The agent commits locally, without pushing. Then, from `verify.md`:

1. The fix differential with `--fix HEAD` reads `FIXED` for both functions, and its control is ok.
2. Two-site regression: `fresh.localhost` at the fix, and `prepatch.localhost` installed at the
   base. On the pre-patch site, the `Library Loan` permissions are edited first, so Custom DocPerm
   rows exist. Then the agent checks out the fix and runs `bench --site prepatch.localhost migrate`.
   The mirror patch is in `Patch Log`, and `Librarian` now has `select` on `Library Loan`.
3. Identity matrix on both sites, with the return values for the same input:

   | Identity | Before | After |
   | --- | --- | --- |
   | Library Manager | 3 rows | 3 rows |
   | Librarian (loser) | 3 rows | 3 rows |
   | Member who owns MEM-0042 | 3 rows | 3 rows |
   | Member who owns MEM-0007, asking for MEM-0042 | 3 rows | 0 rows (User Permission) |
   | System User with no roles | 3 rows | `PermissionError` (no `select` on Library Loan) |
   | Website User with no role | 3 rows | `PermissionError` |
   | `member=["like", "%"]` as a Librarian | every member's rows | refused by the type check |

   The fenced member gets an empty list, not an error. `get_list` drops the records a user cannot
   see, and raises only when the user has no permission on the DocType. This is why the matrix
   compares return values.

### `workflow.md` step 6: review

A separate agent reviews the diff with `frappe-code-review`, using the review brief of
`workflow.md` step 6, with the backport line filled in. It confirms that each API the diff calls
exists on frappe 15 and applies permissions there. It has no findings.

### `workflow.md` step 7: ship without disclosing

The human approves, and the agent pushes:

```text
title     fix(api): use permission-aware queries for member loans and fines
commit    fix(api): use permission-aware queries for member loans and fines
branch    fix/member-loans-access
base      version-15
body      DocPerm: Library Loan, Librarian: select, read
          Patch: mirror Librarian select and read to customized sites
```

The payloads and the identity matrix stay in the private record.

### `workflow.md` step 8: release, then disclose

```text
$ git tag --contains <version-15's merged sha>  -> v1.9.4
```

`main` already released its fix in `v2.4.2`. Both supported branches now have a released fix, so the
advisory names `2.4.2` and `1.9.4` as the patched versions. It is published only now.

### Report

```text
branch     version-15 (frappe version-15-hotfix)
cause      get_all on a caller-chosen member, in get_member_loans and get_member_fines
change     backport of 7c41e2a: get_list + type check, Librarian DocPerm rows, mirror patch
differs    get_member_fines: get_list, because frappe 15's get_query has no permission mode
verified   control refused, allowed calls unchanged, both sites pass, 2 tests fail -> pass
review     no findings
open       none: main is fixed in v2.4.2
```
*(illustrative)*
