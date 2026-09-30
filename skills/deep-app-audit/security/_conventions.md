# Conventions for the security audit

Every file in this directory assumes these conventions. A file never repeats them. Read this file
first, then read the one scope or check that you were given.

`quality/_conventions.md` has the same sections for the quality audit.

## Files

- **Scopes** live in the area directories (`A-authorization`, `B-injection`, and so on). Each
  scope hunts for one class of reachable defect. Everything below applies to scopes: the finding
  bar, the severity ladder, the verification, and the finding format.
- **Checks** live in `checks/`. Each check reports posture over the whole surface: a coverage
  percentage, a diff against a baseline, or a table of what is set and what is missing. A check
  cannot state an entry point, an actor, and an impact, so the finding bar does not apply to it
  and nothing verifies it. It follows its own `## Task` and `## Output` sections, and its table
  goes to the report appendix.

If a check finds something that clears the finding bar, report it as a finding and name the scope
it belongs to. Do not force a posture gap into the finding format to make the list look longer.

The file name is `<id>-<slug>.md`. A scope has this format:

```markdown
---
id: A02
area: authorization
---
# A02 — Title

**Scope:** what the scope covers, and where it stops.

**Why:** what the attacker gets, and why the defect occurs.

**Applies to:** optional. The condition that makes the scope relevant.

## Find

## Confirm

## Report
```

- `## Find`: the search signals that find candidates, usually `rg` patterns and code shapes.
- `## Confirm`: how to tell a true positive from a false positive.
- `## Report`: optional. What a finding of this scope must state in addition to the fields in
  "Output".

A check has `**Kind:**`, `**Why:**`, an optional `**Applies to:**`, then `## Task`, an optional
`## Inputs` and `## Confirm`, and `## Output`.

## Target

You audit a Frappe app checkout. The prompts apply to any Frappe app: the framework, a
first-party app, or a custom app. Do not assume an app name, a module layout, or a file path.
Find the real paths in the checkout that you were given. File paths in a prompt are examples from
the framework. They are search hints, not a promise that the file exists in your target.

Audit application code. Do not audit `node_modules`, `.git`, vendored assets, or generated files.

When a prompt has an `**Applies to:**` line and the target does not match it, say so in one line
and stop. That is a correct result, not a failure. Do not invent findings to fill the report.

## Method

1. Use the `## Find` section to get candidates. Use the entry-point inventory when there is one,
   then `rg`. Cast wide, then narrow.
2. When the run has semgrep matches, add the matches of the rules in `rules/security` of the
   semgrep rules that fit your scope. Read the rule to know what it matches.
3. For each candidate, read enough of the code around it to know who can reach it and with what
   input.
4. Trace reachability. Find a path from an HTTP request to the sink: a whitelisted method, a
   DocType controller method, a hook, a portal route, a socketio handler, or a scheduled job that
   reads user data. Unreachable code is not a finding.
5. Apply the `## Confirm` section.
6. Discard anything that you cannot state as a concrete attack.

## Live test site

Your task can give you a disposable Frappe site with the app installed and one test user for
each actor level. When it does:

- Use the site to settle what you cannot settle by reading. Log in as the stated actor, send the
  request, and record the status and the body that came back. A recorded response is better than
  any reasoning about what the code does.
- A 403, a `PermissionError`, or a validation failure refutes the finding as reported. Name the
  control that produced it.
- Prove the impact, do not maximise it. Read one record that you must not read. Do not destroy
  data, and never run a payload that leaves the machine. For SSRF and outbound scopes, point the
  payload at a local listener that you start yourself.
- A finding whose preconditions only Administrator can create is weaker. Say so.
- Use only the site that you were given. Never touch another site on the bench, and never change
  a file in the app checkout.
- A failed attempt is evidence too. Record exactly what came back.
- **Check the site configuration before you trust a response.** A test bench is not a production
  bench. `ignore_csrf`, `developer_mode`, `allow_tests`, `server_script_enabled`, and similar
  keys each disable a control that a real site keeps. A request that succeeds only because one of
  them is set proves nothing about production. Your task tells you which of these are set. When a
  result depends on one, say so on the finding, keep only the part that stands without it, and
  state what must be tested again.

Without a site, every claim must come from the code, cited by file and line.

## What counts as a finding

A finding needs all four:

- **Entry point**: the exact reachable function or route.
- **Actor**: Guest, Website User, plain System User, or a named low-privilege role.
- **Input**: the request-controlled value, and how it reaches the sink.
- **Impact**: what the actor reads, writes, or executes that they must not.

When you cannot state all four, it is not a finding. Say so and continue. A short list of real
findings is better than a long list of possible ones.

One defect is one finding. When one cause reaches several entry points, report it once and list
every entry point. A fix to one line must not close five findings.

## Known non-findings

- Code guarded by `frappe.only_for`, `check_permission`, `has_permission`, or an equal explicit
  check that covers the actor and the object.
- `ignore_permissions=True` in code that only a scheduled job, a patch, an install script, or a
  test can reach.
- A sink whose input is a constant, or a value already checked against a fixed allowlist.
- Code that only Administrator or System Manager can reach, when the impact does not exceed what
  that role can already do. Note it as informational at most.

## Severity

- **Critical**: Guest or any authenticated user gets remote code execution, arbitrary SQL, a full
  data read, or account takeover.
- **High**: a low-privilege user crosses a trust boundary. Examples: the user reads or writes the
  data of another user, tenant, or company, or escalates a role.
- **Moderate**: a partial disclosure, a bypass that needs an unusual precondition, or a control
  that fails only in a specific configuration.
- **Low**: enumeration, a metadata leak, or missing defence in depth.

The actor decides most of the severity. What a System Manager can already do is not a finding
when they do it another way.

## Verify

An independent agent verifies each candidate in a fresh context. The verifier did not find the
candidate, and tries to refute it. The verifier works in this order:

1. Read the cited code, and enough of the code around it to know what occurs. Do not trust the
   quoted excerpt or the quoted line number. Verify both.
2. **Reachability.** Trace a real path from an HTTP request to the sink. When there is no path,
   reject.
3. **Proof.** Write the concrete request that the stated actor sends, with the parameter values
   that start the defect. When you cannot write that request, reject. When there is a live test
   site, send the request as that actor, and record what came back. When the request needs a
   fixture that the site does not have, create the fixture as Administrator, then send the
   request as the low-privilege actor.
4. **Guards.** Look for a permission check, a validation, a decorator, or a guard in a caller
   that the finder missed. Look several frames up the call chain. A guard that covers this actor
   and this object rejects the finding.
5. **Environment.** When the test site sets a key that weakens a control, decide if your result
   depends on it. When the request fails on a site without that key, mark the finding as
   dependent on the environment, state the caveat, and keep the verdict only for the part that
   stands without the key.
6. **Severity.** Assign it yourself from the ladder above. Do not copy the reported severity:
   finders overstate.
7. **Correct the record.** When the finding is real but the file, the line, the actor, the
   input, or the impact is wrong, confirm it and give the correct values.

## Output

This section applies to scopes. A check follows the `## Output` section of its own file.

Report findings as a list, most severe first. Use Markdown. Give one heading per finding, then a
bullet list. Use inline code for paths, symbols, and values. Use fenced blocks only for real code
extracts.

### [SEVERITY] one-line title

- **Id:** the scope id, for example `S-A02`
- **File:** `path/to/file.py:123`
- **Actor:** who
- **Input:** the request-controlled value
- **Impact:** what they get
- **Proof:** the call chain, 1 to 3 lines
- **Evidence:** what was run on the test site and what came back, or `not executed`
- **Caveat:** only when the result depends on a weakened site setting. Name the setting, say what
  the result does not show, and say what must be tested again. Put it on the finding: a caveat
  that is only in a summary is not visible to a person who triages one finding.

End with a coverage line: what you searched, what you did not search on purpose, and what you
could not resolve.
