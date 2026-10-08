# Fix a security vulnerability in a Frappe app

The security path of `fix-issue`, for any Frappe app. It runs only from `/fix-issue`, after step 1
of `SKILL.md` has returned the brief, and it replaces steps 2 to 6 of that file.

The fix is done when four things are true:

- The flaw is gone on every release line.
- Every legitimate user still gets what they got before.
- A release carries the fix.
- Nothing public described the flaw before that release.

Terms used in these files:

- **release line**: a branch the app still ships from and accepts fixes on. Each app has its own
  set: `develop` alone, `main`, or `develop` plus `version-N-hotfix` lines.
- **branch unit**: the fix for one release line, done by its own agent in its own bench, with its
  own pre-flight, fix, verification and review. Units run in parallel.
- **branch ledger**: one column per release line, one row per piece of evidence
  ([template](units/branch-ledger.md)). The fix is done when every cell is filled.
- **fix differential**, **known-positive control**, **two-site regression**: defined in
  [verify.md](verify.md).
- **the line's frappe**: the frappe major a release line runs on. Each unit writes its fix against
  it, as [frappe-versions.md](frappe-versions.md) says.

Work from the brief. When it is thin, `SendMessage` the extractor agent, as `SKILL.md` says.

## Steps

### 1. Triage: pin the flaw to code

Take from the brief every **location** the evidence names, the **actor** and the **input**. A
location is an endpoint, a stored field or a sink, and one report often names several. The request
path in a proof of concept is evidence and stays in the brief.

Done when: each location is a file and a function in the app, with the actor and input that reach
it.

### 2. Reproduce: the known-positive control

Send the brief's request as the brief's actor, on one release line, and see the flaw happen. That
payload is the known-positive control every branch unit runs.

The three end states of `SKILL.md` step 2 apply. Before you report "cannot reproduce", read the
function at the head of every release line: one line can carry a fix the others lack.

Done when: the payload works on at least one line, or each line has a written reason it does not.

### 3. Find the release lines

```bash
scripts/release_lines.sh <app-checkout>
```

It lists each development and release branch with its last commit, the frappe range from
`[tool.bench.frappe-dependencies]`, and a verdict. Where `version-N` and `version-N-hotfix` both
exist, the hotfix branch takes the fix and releases are cut into `version-N`.

**The human confirms the list.** Which lines an app still supports is a policy decision. Branch
activity is evidence of it.

Done when: the human has confirmed the release lines, and each has a frappe branch read from its
`frappe-dependencies` range.

### 4. Classify, and find the other half

| The brief shows | Reference |
| --- | --- |
| a caller reads or changes records they have no permission for: `get_all`, `get_doc` or `frappe.qb` on caller input, a missing role gate | [missing-authorization.md](classes/missing-authorization.md) |
| user input in SQL: values, `fields`, `filters` keys, sort keys, DocType names | [sql-injection.md](classes/sql-injection.md) |
| user text rendering as HTML or script | [xss.md](classes/xss.md) |
| user-written Jinja, formulas or method paths evaluated on the server | [template-code-injection.md](classes/template-code-injection.md) |
| a caller-supplied path, file, URL, redirect, XML document, archive or export value | [file-and-url-handling.md](classes/file-and-url-handling.md) |
| CSRF or a GET state change, type confusion, mass assignment, bypass flags, rate limits | [input-and-request-handling.md](classes/input-and-request-handling.md) |
| login, tokens, keys, reset links, enumeration, data in errors or emails | [auth-and-disclosure.md](classes/auth-and-disclosure.md) |

**The other half:** one function often carries two flaws. An injection fix adds no permission
check. A permission check leaves operator injection through a `filters` dict. Escaping one argument
leaves its siblings. Check every endpoint you touch against the authorization reference as well as
its own class.

**The sibling sweep:** search the app for the same sink — the helper other endpoints call, the
same template pattern, the same `render_template` on other fields. Each instance of the flaw is
part of this fix, so `SKILL.md`'s "no adjacent fixes" leaves it in scope. Fix every reachable
instance, or write down why one is unreachable.

Done when: every endpoint in scope is checked against every class it touches, and the sweep's list
of instances is written down.

### 5. Set up one branch unit per release line

Find a bench whose app checkout tracks each release line. When one is missing, ask the human for
its path, or set it up with [bench-setup.md](units/bench-setup.md). Then check them:

```bash
scripts/bench_status.sh <app> <line>=<bench> [<line>=<bench> ...]
```

`READY` means on the target branch, clean, and level with the remote. Any other verdict means work
is in progress there: ask its owner before you use that bench.

Open the branch ledger with one column per release line.

Done when: every release line has a `READY` bench, and the ledger has a column for each.

### 6. Run the branch units in parallel

Spawn one `general-purpose` agent per release line, working in that line's bench, with the brief
from [branch-unit-brief.md](units/branch-unit-brief.md). Each line gets a new agent: an agent that
has worked on one line carries its file layout and frappe APIs into the next, where a check written
for the wrong layout reads correct and does nothing.

Each unit:

1. **Pre-flight.** `scripts/preflight.sh <bench>/apps/<app> <line> <fix-branch>` cuts the fix
   branch from the remote head. The unit then runs the known-positive control at that head. When
   the line is already fixed, the unit stops and reports the sha: that corrects the ledger and is a
   result.
2. **Port or write, against the line's frappe.** Probe with `git cherry-pick -n <sha>` from a fixed
   line. Then read every frappe API the fix calls at this line's frappe branch, as
   [frappe-versions.md](frappe-versions.md) says. Keep the pick only when it applies and each API
   exists and behaves as the fix needs. Otherwise write the fix with the class reference, using the
   line's equivalent for each API that differs. Endpoints also move between majors.
3. **Verify.** The class reference's payloads before and after, the fix differential at the unit's
   head, and the two-site regression on this line's bench.
4. **Review.** A separate review agent, as in `SKILL.md` step 5, given the brief's symptom and actor.
   The unit acts on the findings and verifies again.
5. **Commit and open the pull request** against the line, as step 8 describes.

Before writing a port, check for one a backport bot has already opened:
`gh pr list --search "<parent-pr> in:title,body" --state all`. Bots open them within a minute of a
merge.

Done when: every unit has reported its ledger column filled with evidence, or a written reason its
line needs no change.

### 7. Converge the units

Read the units' diffs side by side. Keep helper names, guard shapes, patch file names and
`patches.txt` lines the same on every line. They differ only where the line's frappe forces it, and
each such difference matches a row of [frappe-versions.md](frappe-versions.md) or a body the unit
read.

Done when: every difference between lines has a written reason, and the ledger is complete.

### 8. Ship without disclosing

The pull request is public when it opens, and the fix protects no one until a release carries it.
Everything public describes the change, never the flaw.

- Write the title and commit subject as an ordinary fix in the app's convention:
  `fix(<module>): add permission checks on <feature> methods`.
- Use plain change language in the title, commits, branch name, code comments and test names. The
  words security, vulnerability, exploit, CVE, GHSA, XSS, SQLi and IDOR stay in the private record.
- Leave the pull request description empty, or limit it to what an administrator needs: a DocPerm
  change table, a migration patch. GitHub keeps a description's edit history, so text cleared later
  stays readable.
- Keep reproductions, payloads, access matrices and private tracker IDs in the private record.
- Commit and write the message as `SKILL.md` step 6 says.

Done when: the public pull request, commits and code on every line describe only the change.

### 9. Release, then disclose

**Merged is not released.** For each line, `git tag --contains <that line's sha>`. An empty result
means no release carries the fix yet. Read the function at the line's version-sorted tags to find
its first fixed release, and record it in the ledger. Publish the advisory after that, naming
exactly those versions. The human can run `/draft-security-advisory` to write it.

Done when: every ledger column has a first fixed release, and the advisory names exactly those.

## Report

A worked run of every step is in [example.md](example.md).

In place of `SKILL.md` step 6, give the human the ledger, then one line per release line: the
cause, the change, the verification, the review outcome, and anything unresolved.
