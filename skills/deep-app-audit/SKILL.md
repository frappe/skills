---
name: deep-app-audit
description: Deep audit of a Frappe app for security, correctness, and customization defects. Runs every security scope and every quality rule as a separate agent, verifies each candidate in a fresh context, and compiles one report. User-invoked only - run /deep-app-audit [app path] [options].
disable-model-invocation: true
---

# Deep app audit

This skill audits one Frappe app checkout on three tracks and writes one report:

- **Security**: 66 scopes in `security/` (authorization, injection, XSS, and more) and 10
  posture checks in `security/checks/`. `security/_conventions.md` is the contract for these
  prompts.
- **Correctness**: the `B` rules in `quality/B-correctness/`.
- **Customization**: the `A` rules in `quality/A-customization/` and the checks in
  `quality/checks/`.

The quality files are knowledge-base documentation. `quality/_audit.md` turns one rule into an
audit task.

`audit.workflow.js` does the work. It builds an entry-point inventory, starts a disposable test
site, runs one scan agent for each prompt, tries to refute each candidate with a fresh agent, and
compiles the result. Do not audit the app yourself.

## 1. Read the arguments

The argument is the app checkout to audit, then options in plain words. With no path, use the
current directory. Map the options to workflow `args`:

| Option | `args` key | Example |
|---|---|---|
| audit a part only | `only`: id prefixes | `["S-A", "Q-B05"]` |
| leave a part out | `skip`: id prefixes | `["S-L", "S-P05"]` |
| no whole-surface checks | `noChecks: true` | |
| no test site, read the source only | `noSite: true` | |
| reuse a site | `site` | `"myapp-audit.localhost"` |
| database root password | `dbRootPassword` | |
| bench directory | `bench` | |
| report path | `output` | |
| drop the created site at the end | `dropSite: true` | |
| verification caps | `maxCandidatesPerScope`, `maxVerifications` | `15`, `600` |

The ids have a track prefix:

| Prefix | Prompts |
|---|---|
| `S-A` to `S-L` | security scopes, for example `S-A01` |
| `S-P` | security posture checks |
| `Q-A` | customization rules |
| `Q-B` | correctness rules |
| `Q-K` | customization checks |

"Only security" is `only: ["S-"]`. "Only correctness" is `only: ["Q-B"]`. "Only quality" is
`only: ["Q-"]`.

## 2. Confirm the target

Confirm that the path holds a Frappe app: one package in it holds `hooks.py`. If it does not,
stop and tell the user.

Tell the user in two or three lines what will run: the app, the tracks, whether a test site is
created, and the approximate agent count. A full run is about 160 scan and check agents plus one
agent for each candidate, and it can be several hundred agents. Do not ask for confirmation when
the user gave the path and the options. The command is the opt-in.

The test site phase needs write access to a bench. When the checkout is not in a bench, or the
bench looks like production, use `noSite: true` and say so.

## 3. Run the workflow

Call the `Workflow` tool with:

- `scriptPath`: `<this skill's base directory>/audit.workflow.js`
- `args`: `{"skillDir": "<this skill's base directory>", "target": "<absolute app path>", ...options}`

`skillDir` is required. The workflow reads every prompt from it.

The workflow runs in the background. Wait for its notification. Do not poll, and do not start a
second run.

## 4. Report the result

The workflow returns the report path, the raw findings path, and the counts. Tell the user:

- the report path, and the raw findings JSON path
- the confirmed candidate count for each track and severity, and the refuted and uncertain
  counts. The report folds candidates by root cause, so the report has fewer findings. Read the
  header of the report to get the distinct count.
- the titles of the Critical and High findings, one line each, from the summary table of the
  report
- the test site name, when the run kept one, so the user can reproduce a finding
- anything the run dropped: a failed agent, a scan that a cap left unverified, a check that was
  `not applicable`

Do not copy the report into the reply. Do not propose fixes.

If the report agent failed, the raw findings JSON still holds every verified finding. Tell the
user, and offer to run the report step again from that file.

## Warning

The output is agent output. A human must confirm every finding before anyone acts on it. Expect
false positives and gaps. A clean report does not prove that the app is secure or correct.
