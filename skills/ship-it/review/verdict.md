# Findings and verdict

Every reviewer in this skill reports findings in this format. The verdict is computed from the findings by the table below. A reviewer reports findings. It never picks the verdict or a score.

## Finding

```json
{
  "id": "c1",
  "reviewer": "correctness | taste | <bot login>",
  "severity": "blocker | issue | nit",
  "action": "auto-fix | ask-user | no-op",
  "file": "src/tree.ts",
  "line": 42,
  "title": "short label",
  "description": "what is wrong, the concrete case that shows it, and the remedy",
  "citation": "the rule, intent line, or traced execution path behind it"
}
```

### Severity

- **blocker**: must not merge. A likely shipping bug, data loss, a security hole, an unapproved breaking change, or a broken intent item.
- **issue**: worth fixing before merge. A real defect on a rare path, a structural problem the change introduces, a missing test for changed behavior.
- **nit**: optional. Naming, small readability, a cheap tidy.

A finding without a citation is a nit at most.

### Action

Classify by the **remedy**, not only the topic.

- **auto-fix**: a mechanical fix that changes nothing the intent or the user decided.
- **ask-user**: the finding challenges the intent or product behavior, or its smallest honest remedy would extend the change: new durable state, a schema change, a new subsystem, retry or background machinery. When in doubt, ask-user.
- **no-op**: information only.

## Output

```json
{
  "reviewed_sha": "<full sha>",
  "risk": "low | medium | high",
  "risk_rationale": "one sentence",
  "findings": [ ... ],
  "declined_to_judge": ["what you chose not to judge, one line each"]
}
```

An empty `findings` list is a valid review.

## Verdict

| Tier | ✅ Approve                     | 💬 Approve with comments       | 🛑 Needs work                     |
| ---- | ------------------------------ | ------------------------------ | --------------------------------- |
| prod | 0 blockers, 0 issues, ≤ 3 nits | 0 blockers, 0 issues, 4–5 nits | any blocker or issue, or > 5 nits |
| wip  | 0 blockers, 0 issues           | 0 blockers, some issues        | any blocker                       |

Count only findings still open: fixed findings and those the user decided to skip drop out.

Write the verdict as one line: `✅ Approve · 0 blockers · 0 issues · 2 nits`.

## Rounds

- **Round 1** reviews the whole change.
- **Round 2 and later** review only the commits since the last review, and verify the findings still open. A new finding in code an earlier round already reviewed counts only when it is a blocker.
- **Limit:** the local review loop and the bot loop each get 3 rounds. After a loop's third round, only blockers change the verdict and keep that loop going. The other open findings go to the PR's `## Review` section as follow-ups.
- Code that was already there before this change goes to `declined_to_judge` or a follow-up, never into the count.

## Round comment

Every review round, local or bot, ends with one top-level comment on the PR. Post it when the round closes, so every finding has its outcome:

```markdown
### Review round <n> · <local | bot> · <short sha>

<verdict line>

| #   | Reviewer    | Severity | Finding                  | Outcome                       |
| --- | ----------- | -------- | ------------------------ | ----------------------------- |
| c1  | correctness | issue    | `src/api.py:88` <title>  | fixed in <short sha>          |
| t2  | taste       | nit      | `src/tree.ts:42` <title> | declined: <reason>            |
| t3  | taste       | issue    | `src/tree.ts:90` <title> | skipped by the user: <reason> |

**Declined to judge:** <one line each, when any>
```

Outcomes: `fixed in <sha>`, `declined: <reason>`, `skipped by the user: <reason>`, `follow-up`, or `open`. A round with no findings still gets a comment with its verdict line.

Number round comments in one sequence per PR, local and bot together. This numbering does not count toward the limit above. Before the PR exists, save each local round's comment to `$TMPDIR/ship-it/<repo>-<branch>/round-<n>.md`. Step 8 posts them in order once the PR is created.
