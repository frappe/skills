# Fix a security vulnerability in a Frappe app

The security path of `fix-issue`, for any Frappe app. It runs only from `/fix-issue`, after steps
1 to 3 of `SKILL.md`: the brief is extracted, the flaw is reproduced as its actor (the
known-positive control), and each location is pinned to a file and a function. It replaces steps 4
to 6 of that file.

It fixes **one branch**: the branch of the app checkout in the current bench. Another branch is
its own run, or a backport of this fix, which step 3 cross-verifies against that branch's APIs.

The fix is done when four things are true:

- The flaw is gone on the branch.
- Every legitimate user still gets what they got before.
- A release of the branch carries the fix.
- Nothing public described the flaw before that release.

Terms used in these files:

- **the branch**: the app branch this run fixes, such as `develop` or `version-15-hotfix`.
- **the branch's frappe**: the frappe major the branch runs on. The fix is written against it, as
  [frappe-versions.md](frappe-versions.md) says.
- **backport**: a fix that already exists on another branch, as a commit or as a pull request a
  backport bot opened, carried to this branch.
- **fix differential**, **known-positive control**, **payload sets**, **two-site regression**:
  defined in [verify.md](verify.md).

Work from the brief. When it is thin, `SendMessage` the extractor agent, as `SKILL.md` says.

## Steps

### 1. Pin the branch

Name the branch the app checkout is on, and **ask the human to confirm it** is the branch to fix.
Then read its frappe major from `pyproject.toml`, and confirm that the bench's frappe checkout is
on the matching branch ([frappe-versions.md](frappe-versions.md) step 1).

`<remote>` below is the remote that tracks the official repository, `upstream` by default. Stop and
ask the human when the checkout has uncommitted files or commits the remote lacks: that is someone's
work in progress. Otherwise cut the fix branch from the remote head:

```bash
git -C <bench>/apps/<app> fetch <remote> --tags && \
git -C <bench>/apps/<app> switch --no-track -c <fix-branch> <remote>/<branch>
```

Stop if the fetch fails. Run `bench --site <site> migrate` and `bench build --app <app>` for the
site you test, then run the known-positive control there. Build again after every later change to
JavaScript or templates, and after every checkout switch, or the browser runs old code. When the
branch is already fixed, stop and report the sha.

Done when: the human has confirmed the branch, the fix branch starts at the remote head, and the
control works there.

### 2. Classify, and find the other half

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

### 3. Port or write, against the branch's frappe

First look for a fix that already exists on another branch: a commit the brief or the log names, or
a backport pull request a bot opened (`gh pr list --search "<parent-pr> in:title,body" --state all`).
Bots open them within a minute of a merge.

**A backport: cross-verify it with this branch's APIs.** A backport that applies cleanly can still
call an API this branch's frappe lacks, or one that exists and checks less. It then imports and does
not guard. Never take a backport as is:

1. Apply it to `<fix-branch>` without committing. For a commit, `git cherry-pick -n <sha>`. For a
   bot's pull request, `git fetch <remote> pull/<number>/head` and then
   `git cherry-pick -n <remote>/<branch>..FETCH_HEAD`. Stay on `<fix-branch>`: the tests, the local
   commit and the two-site regression all read it.
2. List every frappe API, keyword argument and app helper the diff calls.
3. Read each one at this branch's frappe, as [frappe-versions.md](frappe-versions.md) step 2 says:
   it must exist, take the arguments the diff passes, and run the checks the fix relies on. The
   table in that file lists the known differences between majors.
4. Replace each one that is missing or weaker with this branch's equivalent. Keep the guard's shape
   and names the same as the original fix, and change only what this branch forces.
5. Confirm that each file and endpoint the diff touches lives at the same path on this branch.
   Endpoints move between majors.

Write down each difference from the original fix, with its reason. The report carries them.

**A new fix:** write it with the class reference, and read every frappe API it calls at this
branch's frappe in the same way.

Done when: every frappe API and app helper the fix calls has been read at this branch's frappe and
does what the fix needs, and every difference from the original fix has a reason.

### 4. Test

Add regression tests to the app's test suite: the control refused, and an entitled identity's call
unchanged, as [regression-matrix.md](classes/missing-authorization/regression-matrix.md) shows. Run
them as the identities they name, never as Administrator. They fail without the fix and pass with
it. Name them for the behaviour, as step 7 says.

Done when: the tests fail on the remote head and pass on the fix.

### 5. Commit locally, then verify

Commit the fix and its tests on the fix branch, with the message step 7 describes. Do not push.
Verification reads this commit, and the pre-patch site of the two-site regression needs a clean
checkout to switch to the base.

Then verify with [verify.md](verify.md): the class reference's payload sets before and after, the
fix check with `--fix HEAD`, and the two-site regression.

Done when: every check in verify.md has its expected result.

### 6. Review in a separate agent

Spawn one `general-purpose` agent, `run_in_background: false`:

> Load the `frappe-code-review` skill and review the change on the fix branch
> (`git diff <remote>/<branch>`, plus any untracked files) on <branch>, which runs frappe
> <frappe branch>. The change is meant to stop this: <the brief's Effect>, by <the brief's Actor>.
> The class reference is <path>. <For a backport: it ports <sha> from <other branch>.>
>
> Judge five things: does the change stop the flaw at its cause on every location and sibling;
> does every entitled caller keep what they had; for a backport, does every frappe API and app
> helper the diff calls exist on this branch's frappe and do what the fix needs; the "Done when"
> lines of the class reference; and the skill's checklist, its Security section first. Report only
> findings worth acting on, most serious first — file and line, what breaks and for whom, the fix.
> No summary of the diff. If nothing is worth acting on, say so in one line.

Act on the findings, amend the local commit, then test and verify again.

Done when: the review has no findings left to act on.

### 7. Ship without disclosing

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
- Push and open the pull request against the branch only after the human approves.

Done when: the public pull request, commits and code describe only the change.

### 8. Release, then disclose

**Merged is not released.** Run `git tag --contains <merged sha>`. An empty result means no release
carries the fix yet. Read the function at the branch's version-sorted tags to find its first fixed
release ([verify.md](verify.md) step 3).

The advisory names a fixed version for every branch the project supports, so publish it only when
each of them has a released fix. Each other branch is its own run, or a backport cross-verified as
step 3 says. The human can run `/draft-security-advisory` to write it.

Done when: the branch has a first fixed release, and the human knows which other branches still
need the fix.

## Report

A worked run of every step is in [example.md](example.md).

In place of `SKILL.md` step 6, give the human five to eight lines: the branch and its frappe, the
cause, the change, each difference from a backported fix and its reason, the verification, the
review outcome, and anything unresolved, including other branches that still need the fix.
