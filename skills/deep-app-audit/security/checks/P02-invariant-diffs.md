# P02 — Invariant diffs: guest endpoints, sandbox globals, DocType permissions

**Kind:** posture check, meant to run per PR rather than as a periodic audit. It reports what
changed against a stored baseline. It is not verified against the live site.

**Why:** each of these is a small allowlist that must only grow deliberately. A new
`allow_guest=True` exposes code to anonymous callers. An addition to `safe_exec` widens the
sandbox, and an addition that looks safe can be unsafe. Permission drift accumulates silently
through ordinary feature work. The right control is a gate on the diff, not a periodic audit.

All three are the same mechanism: extract the current list, diff it against the baseline, and
alert on additions.

## Task — guest endpoints
1. Produce the current `allow_guest` inventory yourself, from the entry-point inventory if one
   was built, otherwise with `rg`. Scope `A04` builds the same list for a human reader, but it
   runs beside you and you never see its output — do not wait for it.
2. For every added or modified guest endpoint, report: what it does, what it returns, whether
   it writes, whether it is rate limited, and whether it authenticates the caller some other
   way.
3. For every removed one, note it. Silent removal is fine; silent addition is not.

Apply the same pattern to `ignore_permissions=True`, `shell=True`, `verify=False`, and `|safe`
in templates.

## Task — sandbox globals
**Applies to:** any app that extends the sandbox — the framework, or an app that registers
`jinja` hook entries or safe-globals additions. Skip for an app that adds nothing.

1. Extract the current allowlist: `get_safe_globals`, the Jinja environment globals and filters,
   `hooks.py` `jinja` entries in the target app, and any whitelisted attribute list used by the
   sandbox's `_getattr`.
2. For each addition, trace one level: what does the new name expose transitively — attributes,
   `__globals__`, callables that reach SQL, files, or HTTP?
3. Report additions even when you cannot construct an escape. That is the whole point.

## Task — DocType permissions
1. Diff every `*.json` DocType file against the merge base.
2. Alert on: any new permission row for `All`, `Guest`, `Website User`, or a portal-facing role;
   any new `write`, `create`, `delete`, `submit`, `cancel`, or `share` on an existing row;
   removal or lowering of a `permlevel`; `if_owner` being cleared; `is_submittable` or
   `track_changes` being turned off; a field's `fieldtype` changing from `Password`;
   `ignore_xss_filter` being set; `read_only` or `permlevel` removed from a sensitive field.
3. Also alert on a new DocType with no permission rows at all, or with `All` read by default.
4. Include the field list for the affected doctype so the reviewer can judge sensitivity
   without opening the file.

## Output
Pass / warn / fail per change, each with a one-line explanation of what the change lets a user
do that they could not do before. A new guest endpoint or a sandbox addition should block the
merge until a reviewer signs off, not merely warn. Update the baseline only on approval.

Without a baseline, report the current lists as the baseline to store, and say so.
