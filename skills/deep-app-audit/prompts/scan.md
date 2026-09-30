You audit a Frappe app for {{track}} defects. Your prompt is {{id}}, and only {{id}}.

1. Read {{skill_dir}}/{{track_dir}}/_conventions.md. It governs everything below.
2. Read {{prompt_path}}. That is your prompt. Audit nothing outside it: another agent has each
   other prompt.
3. When the file has a `mechanism` field, read that page in {{skill_dir}}/quality/mechanisms/.
4. Follow the "Method" section of the conventions.

Report each candidate that clears the finding bar of the conventions. An independent agent
verifies each candidate after you, and tries to refute it. So:
- Do not soften or drop a candidate that you believe. State it plainly.
- Do not add weak candidates. A long list of weak candidates hides the real ones.
- Cite the real file and line. The verifier reads the code, not your extract.

When the file has an `Applies to:` line and the app does not match it, write an empty candidate
list and say so in `coverage`. That is a correct result.

Write {{output}}:
{
  "audit": "milkshake",
  "id": "{{id}}",
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
