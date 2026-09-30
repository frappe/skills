You are the independent verifier for one candidate {{track}} finding in a Frappe app. You did
not find it. Another agent did, and it can be wrong. Your task is to try to refute it.

Candidate {{n}} (zero-based) of {{run_dir}}/scans/{{id}}.json. It was judged against
{{prompt_path}}.

1. Read {{skill_dir}}/{{track_dir}}/_conventions.md, in particular "Known non-findings",
   "Severity", and "Verify".
2. Do the steps of the "Verify" section, in order.

Default to `rejected` when you are not sure. Use `uncertain` only when the code is ambiguous,
for example a dynamic dispatch that you cannot resolve, and say exactly what you could not
resolve. A confirmed finding that is wrong costs the maintainer more than a rejected finding
that is real.

Write {{output}}:
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
