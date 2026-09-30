# Conventions for the quality audit

Every file in this directory assumes these conventions. A file never repeats them. Read this file
first, then read the one rule or check that you were given.

`security/_conventions.md` has the same sections for the security audit.

## Files

- **Rules** live in the area directories: `A-customization` and `B-correctness`. Each rule is one
  practice. You hunt for code that breaks it. Everything below applies to rules: the finding bar,
  the severity ladder, the verification, and the finding format.
- **Checks** live in `checks/`. Each check reports a whole surface as a table. A check follows
  its own `## Task` and `## Output` sections. Nothing verifies a check, and its table goes to the
  report appendix.
- **Mechanism pages** live in `mechanisms/`. They are background, not tasks. Each page describes
  the good use of one customization mechanism and the guards that core keeps. When a rule has a
  `mechanism` field, read that page.

If a check finds something that clears the finding bar, report it as a finding and name the rule
it belongs to. Do not force a gap into the finding format to make the list look longer.

The file name is `<id>-<slug>.md`. A rule has this format:

```markdown
---
id: B05
area: correctness
mechanism: M11
semgrep: {rules: [frappe-manual-commit], coverage: partial}
---
# B05 — Title in the imperative

**Why:** what breaks, and for whom.

**Applies to:** optional. The condition that makes the rule relevant.

## Bad

## Good

## Find

## Confirm
```

- `mechanism`: optional. The id of the mechanism page that the rule is about.
- `semgrep`: optional. The Frappe `semgrep-rules` that check the practice. `coverage` is `full`
  when the semgrep rules find every case, and `partial` when they do not. A match is a candidate,
  not a finding.
- `## Bad` and `## Good`: short code examples. `## Good` shows the accepted practice.
- `## Find`: the search signals that find candidates, usually `rg` patterns and code shapes.
- `## Confirm`: how to tell a true positive from a false positive.

A check has `**Kind:**`, `**Why:**`, an optional `**Applies to:**`, then `## Task`, an optional
`## Inputs` and `## Confirm`, and `## Output`.

## Target

You audit a Frappe app checkout. Do not assume an app name, a module layout, or a file path. Find
the real paths in the checkout that you were given. File paths in a rule are examples from the
framework and from ERPNext. They are search hints, not a promise that the file exists in your
target.

Audit application code. Do not audit `node_modules`, `.git`, vendored assets, generated files,
or tests, unless the rule is about tests.

When a rule has an `**Applies to:**` line and the target does not match it, say so in one line
and stop. That is a correct result, not a failure. Do not invent findings to fill the report.

The rules describe the `develop` branch of Frappe. When the target declares an older framework
version, and the `## Confirm` section of the rule states a different behaviour on that version,
apply the older behaviour.

## Method

1. Use the `## Find` section to get candidates. Use the entry-point inventory when there is one,
   then `rg`. Cast wide, then narrow.
2. For each candidate, read enough of the code around it to know when it runs and with what data.
3. Read the framework source when the rule depends on what the framework does. The bench that
   holds the app usually holds `apps/frappe` and the other apps that the target needs.
4. Apply the `## Confirm` section. A candidate that does not pass it is not a finding.
5. Discard anything that you cannot state as a concrete failure.

## Live test site

Your task can give you a disposable Frappe site with the app installed. When it does:

- The audit reads code. Do not use the site to hunt. Use it only to show that a failure that you
  found by reading does occur: run a patch twice, save a document through the path that you
  traced, or call the hook with `bench --site <site> execute` or `console`.
- A failure that you saw is better than a failure that you reasoned about. Record what you ran
  and what came back.
- Do not force a live proof of a race or of an upgrade. A reading is enough there.
- Use only the site that you were given. Never touch another site on the bench, and never change
  a file in the app checkout.
- A failed attempt is evidence too. Record exactly what came back.

Without a site, every claim must come from the code, cited by file and line.

## What counts as a finding

A finding needs all four:

- **Location**: the exact file, line, and function, hook entry, or DocType.
- **Trigger**: the normal use, the data, or the sequence of events that starts the failure. For
  example: two users submit at the same time, a patch runs a second time, a second app overrides
  the same DocType, the site upgrades to the next major version.
- **Failure**: what goes wrong. For example: wrong data, a lost core step, a crash, a failed
  migrate, a failed install.
- **Impact**: who carries the failure, and how much. For example: every invoice on the site, one
  company, the next person who upgrades.

When you cannot state all four, it is not a finding. Say so and continue. A short list of real
findings is better than a long list of possible ones.

One defect is one finding. When one cause breaks the rule in several places, report it once and
list every location.

A practice that the code breaks, but that causes no failure, is not a finding. Style, naming,
and preference are never findings.

## Known non-findings

- Code that runs only in a test, a one-time script outside the app, or a development command.
- Code that the `## Confirm` section of the rule excludes.
- A guard that exists in a caller, in the framework, or in the schema (a unique index, a
  mandatory field, a lock) and that covers this case. Look several frames up before you report a
  missing guard.
- A difference from the `## Good` example that gives the same result.

## Severity

- **Critical**: silent corruption of stateful data in normal use. Examples: wrong ledger or
  stock entries, lost or duplicated financial records, data loss. Nobody sees an error.
- **High**: a failure in normal use for all users of a feature. Examples: a core step does not
  run, an operation fails every time, migrate or install fails, the app breaks on the next
  upgrade.
- **Moderate**: a failure that needs a less common condition. Examples: concurrent requests, a
  second app, a specific configuration, a re-run patch, a partial failure.
- **Low**: a latent defect or a maintenance hazard. The code works today, but the next change in
  core or in the app is likely to break it.

## Verify

An independent agent verifies each candidate in a fresh context. The verifier did not find the
candidate, and tries to refute it. The verifier works in this order:

1. Read the cited code, and enough of the code around it to know what occurs. Do not trust the
   quoted excerpt or the quoted line number. Verify both.
2. **Reachability.** Decide if the stated trigger occurs in the use of this app: a real call
   path, a hook that is registered, a patch that is listed, a condition that a normal site can
   meet. Dead code, or a trigger that no user or job can cause, rejects the finding.
3. **Proof.** Read the framework source where the failure depends on what core does, and decide
   if the failure occurs. When there is a live test site and it is practical, show the failure on
   the site and record what you ran and what came back.
4. **Guards.** Apply the `## Confirm` section of the rule to this code. When the code passes it,
   reject. A guard in a caller, in the framework, or in the schema that covers this case rejects
   the finding.
5. **Environment.** When the failure shows only because of a site setting that a normal site
   does not have, mark the finding as dependent on the environment and state the caveat.
6. **Severity.** Assign it yourself from the ladder above. Do not copy the reported severity:
   finders overstate.
7. **Correct the record.** When the finding is real but the file, the line, the trigger, the
   failure, or the impact is wrong, confirm it and give the correct values.

## Output

This section applies to rules. A check follows the `## Output` section of its own file.

Report findings as a list, most severe first. Use Markdown. Give one heading per finding, then a
bullet list. Use inline code for paths, symbols, and values. Use fenced blocks only for real code
extracts.

### [SEVERITY] one-line title

- **Id:** the rule id, for example `Q-B05`
- **File:** `path/to/file.py:123`
- **Trigger:** what starts the failure
- **Failure:** what goes wrong
- **Impact:** who carries it
- **Proof:** the code path, 1 to 3 lines
- **Evidence:** what was run on the test site and what came back, or `not executed`
- **Caveat:** only when the result depends on a site setting that a normal site does not have.
  Name the setting, say what the result does not show, and say what must be tested again.

End with a coverage line: what you searched, what you did not search on purpose, and what you
could not resolve.
