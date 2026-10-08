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
- **two-site regression**: run the fix on two *new* sites on the line's bench: a fresh install at the
  fix, and a pre-patch site that was customised and then upgraded with a real `bench migrate`.

Run every step once for each release line. Each line's results fill one column of the branch ledger
([template](units/branch-ledger.md)).

## Steps

### 1. Pin the question

For each release line, write down the **endpoint** (or sink), the **file it lives in on that line**
(files move between majors), the **fix commit** if one exists, and the **refs** you are asking
about: the line's head and its release tags.

Ask *"what endpoint does this guard, and where does that endpoint live on this line?"* A file that is
missing on a line means the code lives somewhere else there. Find it.

Done when: every line has a confirmed file path at each ref you will read.

### 2. Classify each ref

Run the known-positive control first. The script does this itself, and it exits non-zero when the
control fails:

```bash
python3 scripts/fix_differential.py --git-dir <bench>/apps/<app> \
    --path <file-on-this-line> [--fix-path <file-at-fix>] --func <function> \
    --fix <sha> upstream/<line> <tag> <tag>
# --repo owner/name instead of --git-dir reads through the GitHub API
```

| Verdict | Meaning |
|---|---|
| `FIXED` | the body matches the post-fix body |
| `UNFIXED` | the body matches the pre-fix body verbatim |
| `DIVERGED n/m` | neither: the body carries *n* of the *m* lines the fix added. Read the body. A line may be fixed in its own shape, so `0/m` is a prompt to read, not a verdict |
| `ABSENT` | the file is present but the function is not. Find where it lives on that ref |
| `NOFILE` | the file is missing at this ref. The code may live in another file there |

For a new finding with no fix commit, read the body at each ref yourself. Then check for the four fix
shapes that carry no guard call:
- **removal** of the endpoint.
- a **literal argument**, such as `ignore_permissions=False`.
- **`frappe.only_for`**.
- a **guard at the other end**: a validator on the settings DocType that feeds the sink.

Done when: every ref on every line has a verdict, and every `DIVERGED` result has been read and
called fixed, partially fixed or unfixed, in words.

### 3. Check that it was released, not just merged

For each line, run `git tag --contains <that line's own sha>`. An empty answer means the fix sits on
the line with no release. Find the line's first fixed release by reading the function at its
version-sorted tags, because the tag nearest the merge date can be wrong. Where `version-N-hotfix`
feeds `version-N`, the tags are on `version-N`.

Done when: every line has a first fixed release, or is recorded as merged but unreleased.

### 4. Exercise it: the two-site regression

A correct-looking diff can still be a wrong fix. On each line's bench, set up both sites as in
[bench-setup.md](units/bench-setup.md):

1. **Fresh**: a new site at the fix tip, set up and seeded with realistic data.
2. **Pre-patch**: a new site installed at the line's base without the fix, seeded, with the relevant
   permissions customised so that Custom DocPerm rows exist. Then check out the fix and run a real
   `bench migrate`. Confirm the patch ran in `Patch Log`, and confirm that the rows it ships landed.

On both sites, run the class reference's payloads and the identity matrix
([regression-matrix.md](classes/missing-authorization/regression-matrix.md)). For
the same crafted input, capture each identity's **return value** before the fix and after it.

Done when, on both sites: the vulnerable input changes outcome, and every entitled identity gets the
same result after the fix as before it.

## Instruments that have printed clean, wrong answers

| Instrument | What it printed | What answers instead |
|---|---|---|
| A commit-subject search | "unfixed", "no backport" | the function body at the ref. Fixes land as `fix:`/`refactor:`, sometimes saying `perm` rather than `permission` |
| `git branch --contains`, `git cherry`, `git log -S`, `patch-id` | "backport missing" | the fix differential. Backports are squash-merged, so they get a new sha, often a new subject, and sometimes a new layout |
| No `(#NNNN)` in the subject | "no pull request" | `gh api /repos/<owner>/<repo>/commits/<sha>/pulls`, filtered to PRs whose base is the line |
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
