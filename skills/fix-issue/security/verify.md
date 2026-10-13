# Verify a security fix in a Frappe app

**Read the code at the ref, scoped to the function, and run it.** Commit subjects, ancestry, file-wide
greps, merged PRs and suites run as Administrator have all printed clean, confident and wrong answers
on fixes. The question that catches every one of them:

> **Before reporting a measurement, ask what the instrument would print if it were broken. If that
> is indistinguishable from the result in hand, the measurement has not been made yet.**

Three terms the other security files use:

- **known-positive control**: before trusting any probe, point it at a case whose answer you already
  know (the fix commit reads fixed and its parent reads unfixed. The payload fires on the pre-fix
  code). If the control fails, the instrument is broken.
- **fix differential**: classify a function at a ref by comparing its body against the fix commit and
  that commit's parent, using [`scripts/fix_differential.py`](scripts/fix_differential.py).
- **two-site regression**: run the fix on two *new* sites on the branch's bench: a fresh install at
  the fix, and a pre-patch site that was customised and then upgraded with a real `bench migrate`.
- **payload sets**: each class reference splits its checks into three sets, each with its own
  expected result:

  | Set | Before the fix | After the fix |
  |---|---|---|
  | **control**: the brief's attack | works | refused |
  | **probes**: the other attack payloads that reach this sink | record the result. A probe that was already refused is noted with its reason, not counted as a failure | refused |
  | **allowed calls**: what entitled callers do, including the class reference's "allowed" rows | works | works, with the same result |

## Steps

### 1. Pin the question

Write down the **endpoint** (or sink), the **file it lives in on the branch** (files move between
majors), the **fix commit** (`HEAD` for this run's fix, or the original commit of a backport), and
the **refs** you are asking about: the branch's head and its release tags.

Ask *"what endpoint does this guard, and where does that endpoint live on this branch?"* When the
file is missing on the branch, the code lives somewhere else there. Find it, and pass it with
`--fix-path` when it differs from the file at the fix commit.

Done when: the file path is confirmed at each ref you will read.

### 2. Classify each ref

Run the known-positive control first. The script does this itself, and it exits non-zero when the
control fails:

```bash
python3 scripts/fix_differential.py --git-dir <bench>/apps/<app> \
    --path <file-on-this-branch> [--fix-path <file-at-fix>] --func <function> \
    --fix <sha> <remote>/<branch> <tag> <tag>
# --repo owner/name instead of --git-dir reads through the GitHub API
```

| Verdict | Meaning |
|---|---|
| `FIXED` | the body matches the post-fix body |
| `UNFIXED` | the body matches the pre-fix body |
| `DIVERGED n/m` | neither: the body carries *n* of the *m* lines the fix added. Read the body. A line may be fixed in its own shape, so `0/m` is a prompt to read, not a verdict |
| `REMOVED` | the fix removed the function, and it is absent at this ref too. Confirm it did not move to another file |
| `PRESENT` | the fix removed the function, but it exists at this ref in another shape. Read it |
| `ABSENT` | the file is present but the function is not. Find where it lives on that ref |
| `NOFILE` | the file is missing at this ref. The code may live in another file there |
| `UNPARSED` | the file at this ref is not valid Python for the interpreter that runs the script |

The script compares Python tokens, so comments and line wrapping do not change a verdict, and
string contents must match exactly. When another class or function in the file has the same name,
the script refuses to pick one: pass the qualified name, such as `--func LoanRequest.approve`. The extracted function includes its decorators, so a fix that
only adds `methods=["POST"]` reads as a change. When the fix removes the endpoint, the control
expects `REMOVED` at the fix commit.

**A fix outside a Python function** has no function body for the script to compare: JavaScript, a
Jinja or HTML template, DocType JSON, or Python at module level (an import, a constant, a hook).
When the fix leaves the function unchanged, the script's control fails and says so. Check it by
hunk instead:

1. List the hunks the fix changed: `git diff <fix>~1 <fix> -- <file>`.
2. Control: read each hunk's lines at `<fix>` and at `<fix>~1`. They must read fixed and unfixed. If
   you cannot tell them apart, the check is broken.
3. At each ref, find the same code (search by the surrounding lines, not by line number) and call
   each hunk fixed, partially fixed or unfixed, in words.

The payload sets in the browser, on the live DOM, stay the deciding check for these fixes.

For a new finding with no fix commit, read the body at each ref yourself. Then check for the four fix
shapes that carry no guard call:
- **removal** of the endpoint.
- a **literal argument**, such as `ignore_permissions=False`.
- **`frappe.only_for`**.
- a **guard at the other end**: a validator on the settings DocType that feeds the sink.

Done when: every ref has a verdict from the script or the hunk check, and every
`DIVERGED` result has been read and called fixed, partially fixed or unfixed, in words.

### 3. Check that it was released, not just merged

Run `git tag --contains <merged sha>` for the branch's own merged sha. An empty answer means the
fix sits on the branch with no release. Find the first fixed release by reading the function at the
branch's version-sorted tags, because the tag nearest the merge date can be wrong. Where
`version-N-hotfix` feeds `version-N`, the tags are on `version-N`.

Done when: the branch has a first fixed release, or is recorded as merged but unreleased.

### 4. Exercise it: the two-site regression

A correct-looking diff can still be a wrong fix. On the branch's bench, set up two new sites. A
long-lived site carries customisations nobody remembers, and it passes tests that a real upgrade
fails.

1. **Fresh**: a new site at the fix, set up and seeded with realistic data.
2. **Pre-patch**: a new site installed at the branch's base without the fix, seeded, with the
   relevant permissions customised so that Custom DocPerm rows exist. Then check out the fix and run
   a real `bench migrate`. Confirm the patch ran in `Patch Log`, and confirm that the rows it ships
   landed.

```bash
# fresh: at the fix
bench new-site fresh.localhost --install-app <app> --admin-password <pw>

# pre-patch: install at the base, customise, then upgrade to the fix
git -C apps/<app> switch --detach <remote>/<branch>
bench build --app <app>
bench new-site prepatch.localhost --install-app <app> --admin-password <pw>
#   ... complete setup, seed data, and edit the relevant DocType in Role Permission Manager
#   so that Custom DocPerm rows exist ...
git -C apps/<app> switch <fix-branch>
bench --site prepatch.localhost migrate
bench build --app <app>
```

Use a real `bench migrate`. `reload_doc` skips the patch path that an upgrading site goes through.
The fix differential reads `<sha>~1` and the release check reads tags, so a shallow clone needs
`git -C apps/<app> fetch <remote> --unshallow --tags` first.

After every checkout switch on the bench, run `bench build --app <app>` and
`bench --site <site> clear-cache` before a browser check. Otherwise the browser runs the bundled
JavaScript and templates of the previous checkout.

On both sites, run the class reference's payload sets and the identity matrix
([regression-matrix.md](classes/missing-authorization/regression-matrix.md)). For
the same crafted input, capture each identity's **return value** before the fix and after it.

Done when, on both sites: every payload set has its expected result, and every entitled identity
gets the same result after the fix as before it.

## Instruments that have printed clean, wrong answers

| Instrument | What it printed | What answers instead |
|---|---|---|
| A commit-subject search | "unfixed", "no backport" | the function body at the ref. Fixes land as `fix:`/`refactor:`, sometimes saying `perm` rather than `permission` |
| `git branch --contains`, `git cherry`, `git log -S`, `patch-id` | "backport missing" | the fix differential. Backports are squash-merged, so they get a new sha, often a new subject, and sometimes a new layout |
| No `(#NNNN)` in the subject | "no pull request" | `gh api /repos/<owner>/<repo>/commits/<sha>/pulls`, filtered to PRs whose base is the branch |
| A file-wide `grep -c has_permission` | "guarded" | a body-scoped read. The hit belonged to another whitelisted function in the same file |
| A guard-pattern probe on the body | "unguarded" for a literal-argument fix. "guarded" for an ordinary `get_query(` call | the fix differential |
| A `^def ` grep | "function missing" | match `def` at any indentation. Methods are indented |
| A body extractor that stops at `):` | every multi-line signature "unguarded" | step past the whole signature first |
| zsh `git show "$ref:path"` | empty output for every ref | `"${ref}:path"`. Even when quoted, `$ref:` applies a zsh modifier |
| zsh `for x in $LIST` / `for x in $(cmd)` | one iteration | `${=LIST}`, or `while IFS= read -r` |
| A test suite run as Administrator | green | the identity matrix. Administrator short-circuits every permission check |
| A guard read while a backport bot's PR is in flight | "reverted" | `gh pr list --search "<parent-pr> in:title,body"` first |
| A sample selected by the property under test | "N of N affected" | a measured denominator. Ask *"of what?"* |

**A verdict that comes back identical for inputs you know differ is a tooling failure, not a
finding.** So is an absence that holds at every ref, including the ref that introduced the change.

## Reading claims, including your own

- A mechanism with a real `file:line` is a hypothesis until the observation it **predicts** has been
  made. Write down what would differ if it were false, then go and get that observation.
- "Measured" means *this exact variant was run*. Vary the **arguments** as well as the identities.
- A justification ("safe, because the guard above already checks this") is a claim about the code.
  Verify it at every site it names, and most of all when it is the reason a check is being removed.
- A negative is only as wide as what you searched. Say *"not in <set>"*.
- A finding that names several locations is settled only when **every** location has been read, and
  any PR link the report carries has been opened.
