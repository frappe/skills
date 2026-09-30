# Shared conventions for all audit prompts

Every prompt in this directory assumes these rules. Do not repeat them in a prompt; read this
file first, then read the one prompt you were assigned.

## Two kinds of prompt
- **Scopes** live in the area directories (`A-authorization`, `B-injection`, and so on). Each
  hunts for reachable defects. Everything below applies to them: the four-part bar, the
  severity ladder, and the finding format. Their output is verified independently afterwards.
- **Checks** live in `checks/`. Each reports posture over the whole surface: a coverage
  percentage, a diff against a baseline, a table of what is set and what is missing. A check
  cannot state an entry point, an actor, and an impact, so it is not held to the four-part bar
  and it is not verified. It produces its own table, and that table lands in the report
  appendix.

If a check finds something that *does* clear the four-part bar, report it as a finding and name
the scope it belongs to. Do not force a posture gap into the finding format to make the list
look longer.

## Target
You audit a Frappe app checkout. Unless told otherwise, the target is the app in the current
working directory. These prompts apply to any Frappe app: the framework itself, a first-party
app, or a custom app. Never assume a specific app name, module layout, or file path — find the
real paths in the checkout you were given.

Audit application code, not `node_modules`, `.git`, vendored assets, or generated files.

Some scopes carry an `**Applies to:**` line. It tells you when the scope is relevant. If the
target does not match, say so in one line and stop; do not invent findings to fill the report.
File paths named in a prompt are examples from the framework — treat them as search hints, not
as a guarantee that the file exists in your target.

## Method
1. Enumerate candidates with `rg` using the signals in your prompt. Cast wide, then narrow.
2. For each candidate, read enough surrounding code to know who can reach it and with what input.
3. Trace reachability: is there a path from an HTTP request (whitelisted method, doctype
   controller method, hook, portal route, socketio handler, scheduled job with user data) to
   the sink? Unreachable code is not a finding.
4. Discard anything you cannot state as a concrete attack.

## Live test site
Your task may give you a disposable Frappe site with the app installed and one test user per
actor level. When it does:
- Prefer proof by execution. Log in as the stated actor, send the request, and record the
  status and body you got back. A recorded response settles what reading cannot.
- A 403, a `PermissionError`, or a validation failure refutes the finding as reported. Name the
  control that produced it.
- Prove impact, do not maximise it. Read one record you should not read; do not destroy data,
  and never run a payload that leaves the machine.
- Use only the site you were given. Never touch another site on the bench, and never change a
  file in the app checkout.
- A finding whose preconditions only Administrator can create is weaker. Say so.
- **Check the site's configuration before you trust a response.** A test bench is not a
  production one. `ignore_csrf`, `developer_mode`, `allow_tests`, `server_script_enabled` and
  their neighbours each disable a control that a real site enforces, and a request that
  succeeds only because one of them is set has proved nothing about production. Your task tells
  you which of these are set. When a result leans on one, say so on the finding itself, keep
  only the part that stands without it, and state what must be re-tested. An executed proof is
  worth more than a read one — but only when you know what the machine it ran on was doing.

Without a site, every claim must come from the code, cited by file and line.

## What counts as a finding
A finding needs all four:
- **Entry point** — the exact reachable function or route.
- **Actor** — Guest, Website User, plain System User, or a named low-privilege role.
- **Input** — the request-controlled value and how it reaches the sink.
- **Impact** — what the actor reads, writes, or executes that they should not.

If you cannot fill all four, it is not a finding. Say so and move on. A short list of real
findings beats a long list of maybes.

One defect is one finding. If the same root cause reaches several entry points, report it once
and list them — fixing one line should not close five findings. The number of findings is not
the measure of the audit, and a list padded by restating one defect is harder to act on than a
short one, not more thorough.

## Known non-findings
- Code guarded by `frappe.only_for`, `check_permission`, `has_permission`, or an equivalent
  explicit check that actually covers the actor and the object in question.
- `ignore_permissions=True` in code only reachable from a scheduled job, patch, install
  script, or test.
- Sinks whose input is a compile-time constant or a value already validated against a
  hardcoded allowlist.
- Anything only reachable by Administrator or System Manager where the impact does not exceed
  what that role can already do. Note it as informational at most.

## Severity
- **Critical** — Guest or any authenticated user gets RCE, arbitrary SQL, full data read, or
  account takeover.
- **High** — low-privilege user crosses a trust boundary: reads or writes data belonging to
  another user, tenant, or company; escalates role.
- **Moderate** — partial disclosure, bypass that needs an unusual precondition, or a control
  that fails only in a specific configuration.
- **Low** — enumeration, metadata leak, missing defence in depth.

## Output
This section governs scopes. A check follows the `Output` section of its own prompt instead.

Report findings as a list, most severe first. Per finding:

Use Markdown. One heading per finding, then a bullet list. Use inline code for paths,
symbols, and values. Use fenced blocks only for real code excerpts.

### [SEVERITY] one-line title

- **File:** `path/to/file.py:123`
- **Actor:** who
- **Input:** the request-controlled value
- **Impact:** what they get
- **Proof:** the call chain, 1-3 lines
- **Caveat:** only when the result depends on a weakened site setting — name it, say what the
  result therefore does not show, and what has to be re-tested. Put it here, on the finding.
  A caveat that lives only in a summary is invisible to whoever triages this one finding alone.

End with a coverage line: what you searched, what you deliberately skipped, and anything you
could not resolve. Never pad the list to look thorough.
