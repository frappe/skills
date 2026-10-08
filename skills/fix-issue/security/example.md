# Example of the security path

A full fix in a custom app. It starts the way every security fix starts: the human runs
`/fix-issue` on the report. The security path never starts by itself.

---

## A fix in a custom app across two release lines

The app is an invented custom app, `library_management`, which ships from `main` and `version-15`.
Output marked *illustrative* shows the shape of what the agent prints for this invented app.

### The human runs

```text
/fix-issue reports/member-loans.md
```

### `SKILL.md` step 1: the brief

The extractor agent reads the report and returns facts only:

> - **Symptom:** a member can see the loan history of every other member.
> - **Actor:** Website User with the Library Member role.
> - **Request:** `GET /api/method/library_management.api.get_member_loans?member=MEM-0042`, sent
>   by the member who owns `MEM-0007`.
> - **Effect:** the response lists all loans of `MEM-0042`.
> - **Gaps:** none.

The brief has an **Actor** and a **Request**, so the agent follows `security/workflow.md`.

### Step 1: triage

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
> `member`.

### Step 2: reproduce

On `main`, the request from the brief, sent as the member who owns `MEM-0007`, returns the loans of
`MEM-0042`. This payload is the known-positive control for both units.

### Step 3: release lines

```text
$ security/scripts/release_lines.sh ~/lib-main/apps/library_management
BRANCH        LAST-COMMIT FRAPPE                        NEWEST-TAG  VERDICT
main          2026-10-06  ">=16.0.0,<17.0.0"            v2.4.1      CANDIDATE: development
version-15    2026-09-30  ">=15.40.0,<16.0.0"           v1.9.3      CANDIDATE: release line
version-14    2025-11-02  ">=14.0.0,<15.0.0"            v1.2.0      stale (340d)
```
*(illustrative)*

The agent asks:

> I found two active release lines: `main` (frappe 16) and `version-15` (frappe 15). `version-14`
> has had no commits for 340 days. Do I fix `main` and `version-15` only?

The human confirms. The ledger gets two columns.

### Step 4: classify

`frappe.get_all` on a caller-supplied filter points to `classes/missing-authorization.md`. Then:

> - **Other half:** `member` reaches only a filter value, so the query has no injection. It arrives
>   as a filter value, so it also gets a scalar check from `classes/input-and-request-handling.md`.
> - **Sibling sweep:** `grep -rn 'frappe.get_all("Library' library_management/` finds two more
>   whitelisted reads: `get_member_fines`, with the same shape (fix it), and `get_catalogue`, which
>   is public by design (recorded as unreachable).

### Step 5: benches

```text
$ security/scripts/bench_status.sh library_management main=~/lib-main version-15=~/lib-15
=== main                 /home/dev/lib-main/apps/library_management
    verdict  READY
=== version-15           /home/dev/lib-15/apps/library_management
    verdict  READY
```
*(illustrative)*

### Step 6: two branch units in parallel

The agent fills in `units/branch-unit-brief.md` twice and spawns one agent per bench. Each unit:

**Pre-flight**

```text
$ preflight.sh ~/lib-15/apps/library_management version-15 fix/member-loans-access
on fix/member-loans-access, cut from upstream/version-15 at 4be21c0
next: re-verify the flaw at this head before writing anything.
```

The known-positive control works at that head, so the flaw is present on this line.

**Fix**, from `missing-authorization.md` step 2: the sink is `get_all`, so the guard is `get_list`.
`member` is a caller-supplied value, so it gets the scalar check, and `get_list` raises frappe's
own `PermissionError` for a user with no permission on `Library Loan`.

```diff
 @frappe.whitelist()
 def get_member_loans(member: str):
-	return frappe.get_all(
+	member = cstr(member)
+	if not member:
+		frappe.throw(_("Member is required"))
+	return frappe.get_list(
 		"Library Loan",
 		filters={"member": member},
 		fields=["name", "book", "issued_on", "returned_on"],
 	)
```

The sibling `get_member_fines` sums fines per member with `frappe.qb`. Each unit reads the frappe API
at its line's frappe, as `frappe-versions.md` says:

- On `main` (frappe 16), `frappe.qb.get_query("Library Fine", ..., ignore_permissions=False)` applies
  the permissions, so the unit keeps the aggregate query.
- On `version-15` (frappe 15), the query engine has no permission mode. That unit uses
  `frappe.get_list("Library Fine", fields=["member", "sum(amount) as total"], group_by="member")`
  instead, runs it on its own bench, and reports the difference.

**Loser set**, from step 3: `get_list` authorizes on `select`.

```text
roles with write on the calling form (Library Member)   = Librarian, Library Manager
roles with select/read on Library Loan                  = Library Manager, Library Member
losers                                                  = Librarian
```

**DocPerm rows**, from step 4: the unit grants `Librarian` `select` and `read` on `Library Loan` in
`library_loan.json`, and sets `modified` to the current datetime:

```bash
$ python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))"
2026-10-08 10:14:52.381907
```

It adds a Custom DocPerm mirror patch for sites that already customized `Library Loan`, as
`missing-authorization/docperm-shipping.md` says. The guard, the rows and the patch go in one commit.

**Portal callers:** members see their own loans on `www/my-loans.py`. Members hold the app's
`Library Member` role, which has `read` on `Library Loan`, and a User Permission on their own
`Library Member` record. `get_list` applies that User Permission, so each member gets their own
rows. The unit opens the page as a member to confirm it.

**Verify**, from `verify.md`:

1. The fix differential at the unit's head reads `FIXED`, and its control is ok.
2. Two-site regression: `fresh.localhost` at the fix, and `prepatch.localhost` installed at the
   base. On the pre-patch site, the `Library Loan` permissions are edited first, so Custom DocPerm
   rows exist. Then the unit checks out the fix and runs `bench --site prepatch.localhost migrate`.
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
   | `member={"like": "%"}` as a Librarian | every member's rows | 0 rows (`cstr` makes a literal string) |

   The fenced member gets an empty list, not an error. `get_list` drops the records a user cannot
   see, and raises only when the user has no permission on the DocType. This is why the matrix
   compares return values.

**Review:** a separate agent reviews the diff with `frappe-code-review`. It has no findings.

**Report back:** each unit returns one ledger column.

### Step 7: converge

```text
                         main                          version-15
base head at pre-flight  9d0e7a1                       4be21c0
flaw at head             vulnerable                    vulnerable
fix shape                written                       cherry-picked from main, 1 change
frappe APIs read         get_query: ok                 get_query: no permission mode
fix differential         FIXED, control ok             FIXED, control ok
payloads                 worked -> refused             worked -> refused
other half               scalar check added            scalar check added
sibling sweep            get_member_fines fixed        get_member_fines fixed
fresh site               fresh.localhost: pass         fresh.localhost: pass
pre-patch + migrate      patch in Patch Log, pass      patch in Patch Log, pass
review                   no findings                   no findings
differences              -                             get_member_fines: get_list (frappe 15)
pull request             <link>                        <link>
```
*(illustrative)*

The one difference has a reason, so the units have converged.

### Step 8: ship without disclosing

```text
title     fix(api): use permission-aware queries for member loans and fines
commit    fix(api): use permission-aware queries for member loans and fines
branch    fix/member-loans-access
body      DocPerm: Library Loan, Librarian: select, read
          Patch: mirror Librarian select and read to customized sites
```

The payloads and the identity matrix stay in the private record.

### Step 9: release, then disclose

```text
$ git tag --contains <main's merged sha>        -> v2.4.2
$ git tag --contains <version-15's merged sha>  -> v1.9.4
```

The advisory names `2.4.2` and `1.9.4` as the patched versions. It is published only now.

