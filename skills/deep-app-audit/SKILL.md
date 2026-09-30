---
name: deep-app-audit
description: Deep audit of a Frappe app for security, correctness, and customization defects. Runs every security scope and every quality rule in a separate agent, verifies each candidate in a fresh context, and compiles one report. User-invoked only - run /deep-app-audit [app path] [options].
disable-model-invocation: true
---

# Deep app audit

This skill audits one Frappe app checkout on three tracks and writes one report:

| Track | Prompts | Id prefix |
|---|---|---|
| Security | the scopes in the area directories of `security/` | `S-A` to `S-L` |
| Security | the posture checks in `security/checks/` | `S-P` |
| Correctness | the rules in `quality/B-correctness/` | `Q-B` |
| Customization | the rules in `quality/A-customization/` | `Q-A` |
| Customization | the checks in `quality/checks/` | `Q-K` |

The id of a prompt is its track prefix and its file id: `security/A-authorization/A02-*.md` is
`S-A02`. `quality/mechanisms/` is background for the quality rules, not a set of prompts.

Both tracks work the same way. `security/_conventions.md` and `quality/_conventions.md` have the
same sections, and each one is the contract for its track: the method, the finding bar, the
severity ladder, the verification steps, and the finding format. The prompts in this file are
the same for both tracks, and they point each agent to the conventions of its track.

You are the coordinator. Do not audit the app yourself. You prepare the run, start one agent for
each task, and track the result files.

## Agents

Each scan, each verification, each check, and the report runs in its own agent, with a fresh
context. This is necessary: a verifier that saw the scan is not independent, and one context
cannot hold 160 scans. Use the subagent feature of your agent harness. Run agents in parallel
when the harness allows it.

When your harness cannot start agents with a fresh context, tell the user. Offer a small run with
the `only` option instead, done in sequence.

Every agent writes its result to a file in the run directory, and returns only a one-line
summary to you. You never need the full result in your own context. A task whose result file
exists is complete, so a stopped run continues where it stopped.

## 1. Read the arguments

The argument is the app checkout to audit, then options in plain words. With no path, use the
current directory.

| Option | Example | Default |
|---|---|---|
| `only`: id prefixes to run | `S-A`, `Q-B05` | everything |
| `skip`: id prefixes to leave out | `S-L`, `S-P05` | nothing |
| `no checks`: run no whole-surface check | | checks run |
| `no site`: read the source only | | create a site |
| `site`: reuse an existing disposable site | `myapp-audit.localhost` | create one |
| `db root password`: for `bench new-site` | | none |
| `bench`: the bench directory | | found above the checkout |
| `output`: the run directory | | `<target>/../<app>-deep-audit/` |
| `semgrep rules`: a local clone of `frappe/semgrep-rules` | `~/src/semgrep-rules` | clone into the run directory |
| `no semgrep`: do not run the semgrep rules | | semgrep runs |
| `drop site`: drop the created site at the end | | keep it for triage |
| `max candidates`: verification cap for each scan | `15` | `15` |
| `max verifications`: verification cap for the run | `600` | `600` |

"Only security" is `only: S-`. "Only correctness" is `only: Q-B`. "Only quality" is `only: Q-`.

## 2. Confirm the target

Confirm that the path holds a Frappe app: one package in it holds `hooks.py`. If it does not,
stop and tell the user.

Tell the user in two or three lines what will run: the app, the tracks, whether a test site is
created, and the approximate agent count. A full run is about 160 scan and check agents, plus one
agent for each candidate. It can be several hundred agents. Do not ask for confirmation when the
user gave the path and the options. The command is the opt-in.

The test site needs write access to a bench. When the checkout is not in a bench, or the bench
looks like production, use `no site` and say so.

## 3. Prepare the run

Do this yourself. Change no file inside the app checkout.

1. Resolve the checkout to an absolute path. Record the app package name (the directory that
   holds `hooks.py`) and the short commit hash from `git -C <target> rev-parse --short HEAD`.
2. Find the bench, read-only. A bench directory holds `sites/`, `apps/`, and `Procfile`. An
   installed app is usually at `<bench>/apps/<app>`. Record the Frappe version from
   `apps/frappe/frappe/__init__.py`, and the apps that the target requires (`required_apps` in
   `hooks.py`, `pyproject.toml`) or imports, with the path of each on the bench.
3. Create the run directory. When it already holds `setup.json`, this is a resumed run: read it,
   and skip to the first step that is not complete.
4. Build the entry-point inventory:

   ```
   python <skill dir>/scripts/build_inventory.py <run dir>/inventory.json --root <target>
   ```

   The script is read-only. It needs no bench, no site, and no database. When it fails, record
   the error. The audit continues without the inventory.
5. Run the Frappe semgrep rules, unless the user gave `no semgrep`. The rules are the source of
   the `semgrep` field of the quality rules, so run them once here, not in each scan.
   1. Get semgrep. When `semgrep` is on `PATH`, use it. Else, when `uv` is on `PATH`, run
      `uv tool install semgrep`, and call semgrep as `uv tool run semgrep`, because the uv tool
      directory is not always on `PATH`. Do not install uv or pip packages in another way.
   2. Get the rules. With the `semgrep rules` option, use that clone as it is. Else, when
      `<run dir>/semgrep-rules` does not exist, clone it:
      `git clone --depth 1 https://github.com/frappe/semgrep-rules <run dir>/semgrep-rules`.
      A clone in the run directory keeps the rules of one run fixed, also when the run resumes.
      Record the short commit hash of the clone.
   3. Scan the checkout, and give each match its bare rule id. Semgrep prefixes the rule id
      with the path of the rules directory, so remove everything up to the last `.`:

      ```
      <semgrep> scan --config <rules>/rules --json --metrics=off --quiet --output <run dir>/semgrep-raw.json <target>
      jq --arg t "<target>/" '[.results[] | {rule: (.check_id | split(".") | last),
        file: (.path | ltrimstr($t)), line: .start.line, message: .extra.message}]' \
        <run dir>/semgrep-raw.json > <run dir>/semgrep.json
      ```

   When one of these steps fails, record the error. The audit continues without semgrep.
6. List the prompts. Include every `*.md` file in the directories from the table above. Exclude
   files whose name starts with `_`. Apply `only` and `skip` to the ids.
7. Write `<run dir>/setup.json`:

   ```json
   {
     "target": "/abs/path/to/app", "app": "myapp", "commit": "abc1234",
     "bench": "/abs/path/to/bench", "frameworkVersion": "16.0.0-dev",
     "dependencies": [{"app": "erpnext", "path": "/abs/path/to/bench/apps/erpnext"}],
     "inventory": "/abs/run/dir/inventory.json", "inventoryError": null,
     "semgrep": "/abs/run/dir/semgrep.json", "semgrepRules": "/abs/run/dir/semgrep-rules",
     "semgrepRulesCommit": "def5678", "semgrepError": null,
     "scans": ["S-A01", "Q-B05"], "checks": ["S-P01", "Q-K01"]
   }
   ```

## 4. Start the test site

Skip this step with `no site`. Do it yourself, or give the steps below to one agent. The site
lets verifiers send real requests. Without it, the audit reads the source only.

1. Confirm the bench with `bench --version`, run from the bench directory. When there is no
   bench, continue without a site. Do not install bench or a database server, and do not change
   the configuration of the machine.
2. Get a site. With the `site` option, reuse that site. Confirm first that it is not a
   production site: when it holds real data, stop and continue without a site. Otherwise the
   site name is `<app>-audit.localhost`. When a site with that name exists, reuse it: the audit
   owns that name. Else create it:

   ```
   bench new-site <site> --admin-password audit-admin-pw --no-mariadb-socket [--db-root-password <pw>]
   ```

   The command must never stop at a prompt. When it fails, record the error and continue
   without a site. Never create, change, drop, or migrate another site.
3. Install the apps that the target requires, then the target:
   `bench --site <site> install-app <app>`.
4. Create one test user for each actor level, with the password `audit-user-pw`, `enabled = 1`,
   and no onboarding or password-reset requirement:
   - `milkshake-website@example.com`: Website User, no other role
   - `milkshake-user@example.com`: plain System User, no other role
   - `milkshake-manager@example.com`: System User and System Manager, to compare with what a
     manager can already do
5. Serve the site in the background: `bench serve --port 8199`, from the bench directory. When
   the site needs a `Host` header, record it.
6. Record the configuration that changes how a control behaves. Read
   `sites/common_site_config.json` and the `site_config.json` of the site. Record at least
   `ignore_csrf`, `developer_mode`, `allow_tests`, `server_script_enabled`,
   `disable_website_cache`, `maintenance_mode`, and every `*_disabled` or `allow_*` key, with its
   value. Mark each key whose value disables or loosens a control as `weakens: true`, with one
   line on the effect. A bench with `ignore_csrf: 1` accepts a cross-site request that
   production rejects, so a 200 from it proves nothing about production.
7. Prove that the site works:
   - `curl -sS -o /dev/null -w '%{http_code}' <base url>/api/method/ping` returns 200
   - a login as `milkshake-user@example.com` through `/api/method/login` returns 200 and sets a
     cookie
   - `bench --site <site> list-apps` shows the app

   When a check fails, continue without a site. A site that half works is worse than no site,
   because verifiers read its errors as evidence.
8. Write `<run dir>/site.json`:

   ```json
   {
     "ready": true, "site": "myapp-audit.localhost", "baseUrl": "http://localhost:8199",
     "bench": "/abs/path/to/bench", "created": true, "apps": ["frappe", "myapp"],
     "users": [{"email": "milkshake-user@example.com", "password": "audit-user-pw", "actor": "plain System User", "roles": []}],
     "adminPassword": "audit-admin-pw", "notes": "needs Host header",
     "config": [{"key": "ignore_csrf", "value": "1", "weakens": true, "effect": "CSRF is not checked"}]
   }
   ```

   Without a site, write `{"ready": false, "reason": "..."}`.

## 5. Run the scans and the checks

Start one agent for each scan and one agent for each check. They are independent, so start them
all together when your harness allows it. Give each agent the context block and its prompt from
"Prompts".

A scan writes `<run dir>/scans/<id>.json`. A check writes `<run dir>/checks/<id>.json`.

## 6. Verify each candidate

When a scan file lands, read its candidates. Sort them by severity, most severe first. Verify at
most `max candidates` of them, and at most `max verifications` in the full run. The caps drop the
least severe candidates first. Record in the scan file how many candidates the caps left
unverified, as `unverified`.

Start one verification agent for each candidate that you keep, with the context block and the
verify prompt. Verification of one scan can start while other scans still run. Candidate `n` of
scan `<id>` writes `<run dir>/verdicts/<id>/<n>.json`, where `n` is its index in the scan file.

## 7. Write the report

When every scan, verification, and check is complete, start one report agent with the context
block and the report prompt. Then, with `drop site`, and only for a site that this run created:
stop `bench serve`, and run `bench drop-site <site> --force`.

## 8. Tell the user

Tell the user:

- the path of the report and of the run directory
- the confirmed candidate count for each track and severity, and the refuted and uncertain
  counts. The report folds candidates by root cause, so it has fewer findings. Read the header of
  the report for the distinct count.
- the titles of the Critical and High findings, one line each, from the summary table of the
  report
- the test site name, when the run kept one, so that the user can reproduce a finding
- anything the run dropped: a failed agent, a candidate that a cap left unverified, a check that
  was `not applicable`, a semgrep step that failed

Do not copy the report into the reply. Do not propose fixes.

When the report agent fails, the run directory still holds every result. Tell the user, and offer
to run the report step again.

## Prompts

Replace each `<...>` with its value. The track directory is `security` for an `S-` id and
`quality` for a `Q-` id.

### Context block

Put this block at the start of every scan, verify, check, and report prompt:

```
Skill directory: <skill dir>
App checkout: <target>. It is read-only: change no file in it, and do not checkout, stash,
or reset it.
Run directory: <run dir>. setup.json holds the facts of this run.

Bench: <bench>, Frappe <version>. The framework and the apps that the target needs are on the
bench, read-only. Read their source when a verdict depends on what core does.
  (Without a bench: "The framework source is not available. Say so when a verdict depends on it.")

Inventory: <run dir>/inventory.json. It is large, so query it with jq. Its `views` object holds
precomputed lists, and each entry point has its file, line, decorators, parameters, permission
checks, and reachable sinks. It is a static approximation: read the real code before you report.
  (Without an inventory: "No inventory is available. Find candidates with rg.")

Semgrep matches: <run dir>/semgrep.json, from the Frappe semgrep rules at <rules dir>. Each
match has `rule`, `file`, `line`, and `message`. Query it with jq by `rule`. A match is a
candidate, not a finding.
  (Without semgrep: "No semgrep matches are available. Use the `## Find` section only.")

Test site: <run dir>/site.json. Use it as the "Live test site" section of your conventions says.
Administrator password: audit-admin-pw. Test users: <email / password / actor, one per line>.
This site sets <key=value, ...>, and each one weakens a control. A result that occurs only
because of one of these keys is not proved for a normal site.
  (Without a site: "No test site is available. Every claim must come from the code, cited by
  file and line.")

Never propose a fix, a patch, or a remediation. The audit reports what is wrong and what it
affects. The fix is the decision of the maintainer, and a wrong suggestion costs more than a
missing one.

Put the marker `milkshake` in all test code that you write, run, or quote: each script, each
`bench execute` or `console` command, each request, each payload, and each record or file that
you create on the test site. Use it in a name, a value, or a comment, for example a record named
`milkshake-po-1`, a parameter value `milkshake' OR 1=1`, or `# milkshake` in a script. The
marker makes each trace of the audit easy to find in site data, logs, and report text. When the
proof needs an exact value that cannot hold the marker, put the marker in a comment or a header
of the same request, for example `X-Audit: milkshake`.
```

### Scan prompt

```
You audit a Frappe app for <track> defects. Your prompt is <id>, and only <id>.

1. Read <skill dir>/<track dir>/_conventions.md. It governs everything below.
2. Read <skill dir>/<track dir>/<file>. That is your prompt. Audit nothing outside it: another
   agent has each other prompt.
3. When the file has a `mechanism` field, read that page in <skill dir>/quality/mechanisms/.
4. Follow the "Method" section of the conventions.

Report each candidate that clears the finding bar of the conventions. An independent agent
verifies each candidate after you, and tries to refute it. So:
- Do not soften or drop a candidate that you believe. State it plainly.
- Do not add weak candidates. A long list of weak candidates hides the real ones.
- Cite the real file and line. The verifier reads the code, not your extract.

When the file has an `Applies to:` line and the app does not match it, write an empty candidate
list and say so in `coverage`. That is a correct result.

Write <run dir>/scans/<id>.json:
{
  "audit": "milkshake",
  "id": "<id>",
  "coverage": "what you searched, what you did not search, what you could not resolve",
  "candidates": [{
    "title": "one line, no severity prefix",
    "severity": "Critical | High | Moderate | Low",
    "file": "path:line, relative to the app checkout",
    "actor": "security only: who sends the request",
    "input": "security only: the request-controlled value, and how it reaches the sink",
    "trigger": "quality only: what starts the failure",
    "failure": "quality only: what goes wrong",
    "impact": "what the actor gets, or who carries the failure",
    "proof": "the call chain or code path, 1 to 3 lines"
  }]
}
Return one line: the id and the candidate count.
```

### Verify prompt

```
You are the independent verifier for one candidate <track> finding in a Frappe app. You did not
find it. Another agent did, and it can be wrong. Your task is to try to refute it.

Candidate <n> of <run dir>/scans/<id>.json. It was judged against
<skill dir>/<track dir>/<file>.

1. Read <skill dir>/<track dir>/_conventions.md, in particular "Known non-findings",
   "Severity", and "Verify".
2. Do the steps of the "Verify" section, in order.

Default to `rejected` when you are not sure. Use `uncertain` only when the code is ambiguous,
for example a dynamic dispatch that you cannot resolve, and say exactly what you could not
resolve. A confirmed finding that is wrong costs the maintainer more than a rejected finding
that is real.

Write <run dir>/verdicts/<id>/<n>.json:
{
  "audit": "milkshake",
  "verdict": "confirmed | rejected | uncertain",
  "severity": "your own reading of the ladder",
  "reasoning": "why it stands or falls, citing the code that you read",
  "reachability": "the path to the defect, or why there is none",
  "tested": true,
  "evidence": "what you ran on the test site and what came back",
  "envDependent": false,
  "envCaveat": "the setting that the proof depends on, and what to test again without it",
  "corrections": "what the candidate got wrong",
  "finding": {"the candidate fields, with your corrections applied"}
}
Set `tested` to true only when you ran the proof on the test site.
Return one line: the verdict and the severity.
```

### Check prompt

```
You run one whole-surface check over a Frappe app. Your check is <id>, and only <id>.

A check is not a hunt for defects. It reports the whole surface: a percentage, a diff against a
baseline, or a table. Nothing verifies it, so report only what you read yourself.

1. Read <skill dir>/<track dir>/_conventions.md, in particular the "Files" section.
2. Read <skill dir>/<track dir>/<file>. Follow its `## Output` section exactly. That table is
   the deliverable.

Report `not applicable` when the check needs a target that this run does not have: a GitHub
organization, a DNS zone, a stored baseline, a core checkout. That is a correct result. Say in
`notes` what you needed.

When you find something that clears the finding bar of the conventions, put it in `findings`
and name the scope or rule it belongs to. Nothing verifies these, so state them with care. A gap
belongs in `gaps`, not in `findings`.

When the check asks for a desired value (a header value, a DNS record, a default), give it. That
is the only exception to the rule on fixes.

Write <run dir>/checks/<id>.json:
{
  "audit": "milkshake",
  "id": "<id>",
  "status": "pass | gaps | fail | not applicable",
  "summary": "two or three lines on the posture today",
  "table": "the table from the Output section of the check, as Markdown",
  "gaps": ["one line for each gap, most important first"],
  "findings": [{"the scan candidate fields, and belongsTo: the scope or rule id"}],
  "notes": "what you could not reach, and why"
}
Return one line: the id and the status.
```

### Report prompt

```
Compile one deep audit report for the Frappe app <app>. Write it to <run dir>/report.md.

The results are in <run dir>. Query them with jq, not by reading them whole:
- setup.json and site.json: the facts of the run.
- scans/<id>.json: the candidates and the coverage of each scan, and `unverified`, the count
  that a cap left unverified.
- verdicts/<id>/<n>.json: the verdict on candidate n of scan <id>. Use `finding` from the
  verdict, not the candidate. Drop every `rejected` verdict.
- checks/<id>.json: the result of each whole-surface check.

Each track has its finding format in the "Output" section of its conventions:
<skill dir>/security/_conventions.md for S- ids, and <skill dir>/quality/_conventions.md for
Q- ids. Read a prompt file when you need its title or its intent.

Start the report with this line, exactly, with the values filled in:

<!-- milkshake deep-app-audit run=<run dir name> app=<app> commit=<short hash> -->

Write these sections, in this order:

- **Header.** The app, the commit, the Frappe version, how many scans and checks ran, and the
  count for each severity in each track. State how the findings were verified: on the live test
  site (name it, and state how many findings have a recorded result), or by reading the source
  only. Give the commit of the semgrep rules, or say that semgrep did not run.
- **Environment.** Only when site.json has a key with `weakens: true`. Put it directly after the
  header. Name each key, list the findings that depend on it, and say that their proof does not
  show the behaviour of a normal site.
- **Summary.** One table of all distinct confirmed findings in all tracks, most severe first:
  number, severity, track, title, and the ids that found it.
- **Security findings**, **Correctness findings**, **Customization findings.** The confirmed
  findings of each track, most severe first, in the format of the track, with the numbers of the
  summary table. When a section is empty, say so in one line.
- **Unresolved.** The `uncertain` verdicts, by track, each with the question that the verifier
  could not settle.
- **Raised by a check, not verified.** The `findings` of the checks. Say in one line that nothing
  tried to refute them. Never merge them into the confirmed lists.
- **Appendix: coverage.** One table for each track: each id, its title, candidates, confirmed,
  and what it searched and did not search. Name each scan with unverified candidates.
- **Appendix: checks.** One subsection for each check, by track, with its status, its summary,
  and its table as written. List the `not applicable` checks in one line at the end, with the
  reason.
- **Footer.** End the report with these two lines, exactly, with the values filled in:

  ---
  Generated by deep-app-audit (milkshake) for <app> at <short hash>.

Fold by root cause, not by wording. Prompts overlap on purpose: one missing permission hook can
arrive as ten candidates, and one check-then-insert can arrive from a security scope and a
correctness rule. Two entries are the same finding when a fix to one line fixes both. Merge them,
list every id that found it, and keep the strongest statement and the best evidence. When the
entries come from different tracks, put the finding in the track of the highest severity, and
name the other track in one line. For a finding that more than two prompts found, state
`found independently by N prompts`. When the merged entries have different severities, take the
highest and state the range in one line.

State the distinct count as the headline, with the raw count next to it:
`N findings (M confirmed candidates before folding)`.

Rules:
- Report only what is in the results. Do not add findings, and do not audit the app again.
- Do not change the severity that the verdict gives.
- Do not add text to fill space. When a severity band is empty, say so in one line.
- A gap from a check is not a finding. Keep the two apart everywhere.
- For a quality finding, give its rule id. The rule shows the accepted practice.
- Keep a desired value that a check table records. Propose no other fix.

Return one line: the path of the report and the distinct count for each track and severity.
```

## Warning

The output is agent output. A person must confirm each finding before anyone acts on it. Expect
false positives and gaps. A clean report does not prove that the app is secure or correct.
