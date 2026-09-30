# Audit conventions for the quality rules

The files in this directory are documentation, not prompts. `_conventions.md` is their format
contract. This file turns one rule or one check into an audit task. Read it first, then read the
one rule or check you were given.

## Two kinds of file

- **Rules** live in `A-customization` and `B-correctness`. Each rule is one practice. You hunt
  for code that breaks it. Everything below applies to rules: the finding bar, the severity
  ladder, and the finding format. An independent agent verifies each finding afterwards.
- **Checks** live in `checks/`. Each check reports a whole surface as a table. A check follows
  its own `## Task` and `## Output` sections. Nothing verifies a check, and its table goes to the
  report appendix.

Mechanism pages live in `mechanisms/`. They are background, not tasks. When a rule has a
`mechanism` field, read that page for the good use and for the guards that core keeps.

## Target

You audit a Frappe app checkout. Find the real paths in the checkout you were given. File paths
in a rule are examples from the framework and from ERPNext. They are search hints, not a promise
that the file exists in your target.

Audit application code. Do not audit `node_modules`, `.git`, vendored assets, generated files,
or tests, unless the rule is about tests.

When a rule has an `**Applies to:**` line and the target does not match it, say so in one line
and stop. That is a correct result, not a failure.

The rules describe the `develop` branch of Frappe. When the target declares an older framework
version, and the rule's `## Confirm` section states a different behaviour on that version, apply
the older behaviour.

## Method

1. Use the `## Find` section of the rule to get candidates. Cast wide, then narrow.
2. For each candidate, read enough of the code around it to know when it runs and with what data.
3. Apply the `## Confirm` section. It separates a true positive from a false positive. A
   candidate that does not pass `## Confirm` is not a finding.
4. Read the framework source when the rule depends on what the framework does. The bench that
   holds the app usually holds `apps/frappe` and the other apps that the target needs.
5. Discard anything that you cannot state as a concrete failure.

An audit reads code. It does not measure. You may use a live test site when your task gives you
one, to show that a failure occurs. Do not use it to hunt.

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
- A guard that exists in a caller or in the framework and that covers this case. Look several
  frames up before you report a missing guard.
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

## Output

This section applies to rules. A check follows the `## Output` section of its own file.

Report findings as a list, most severe first. Use Markdown. Give one heading per finding, then a
bullet list. Use inline code for paths, symbols, and values. Use fenced blocks only for real code
extracts.

### [SEVERITY] one-line title

- **Rule:** the rule id, for example `B05`
- **File:** `path/to/file.py:123`
- **Trigger:** what starts the failure
- **Failure:** what goes wrong
- **Impact:** who carries it
- **Proof:** the code path, 1 to 3 lines

End with a coverage line: what you searched, what you did not search on purpose, and what you
could not resolve.
