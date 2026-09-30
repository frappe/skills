You run one whole-surface check over a Frappe app. Your check is {{id}}, and only {{id}}.

A check is not a hunt for defects. It reports the whole surface: a percentage, a diff against a
baseline, or a table. Nothing verifies it, so report only what you read yourself.

1. Read {{skill_dir}}/{{track_dir}}/_conventions.md, in particular the "Files" section.
2. Read {{prompt_path}}. Follow its `## Output` section exactly. That table is the deliverable.

Report `not applicable` when the check needs a target that this run does not have: a GitHub
organization, a DNS zone, a stored baseline, a core checkout. That is a correct result. Say in
`notes` what you needed.

When you find something that clears the finding bar of the conventions, put it in `findings`
and name the scope or rule it belongs to. Nothing verifies these, so state them with care. A gap
belongs in `gaps`, not in `findings`.

When the check asks for a desired value (a header value, a DNS record, a default), give it. That
is the only exception to the rule on fixes.

Write {{output}}:
{
  "audit": "milkshake",
  "id": "{{id}}",
  "status": "pass | gaps | fail | not applicable",
  "summary": "two or three lines on the posture today",
  "table": "the table from the Output section of the check, as Markdown",
  "gaps": ["one line for each gap, most important first"],
  "findings": [{"the scan candidate fields, and belongsTo: the scope or rule id"}],
  "notes": "what you could not reach, and why"
}
Return one line: the id and the status.
