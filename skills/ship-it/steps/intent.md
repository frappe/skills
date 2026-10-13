# 1. Intent

The intent is the acceptance criteria every later step judges the change against: reviewers, the test step, the PR body, and the review bots. A vague intent makes every later step guess, so write it complete.

## Source

1. The intent the user passed as an argument (`/ship-it "add X; must not change Y"`).
2. Otherwise, the `## Intent` section of this branch's PR.
3. Otherwise, write it from this conversation and the diff: what the user asked for, the decisions made along the way, and what the commits do.

## Format

Lay the intent out so the user can check it at a glance:

```markdown
> **Goal:** <one sentence: the outcome for the user of the product>

| #   |             | Behavior                                                    |
| --- | ----------- | ----------------------------------------------------------- |
| 1   | ✅ Must     | <a behavior the change must have>                           |
| 2   | ✅ Must     | ...                                                         |
| 3   | 🚫 Must not | <a behavior the change must leave alone or never introduce> |
| 4   | ⏭️ Later    | <related work deliberately left out of this change>         |
```

- One behavior per row, short enough to read without wrapping. Keep the row numbers stable: scenarios, findings, and replies refer to them (`intent #3`).
- The goal is one plain sentence that names who benefits and what they can do, or what behavior becomes reliable. Assume the reader has no context from this conversation. Name the concrete outcome; replace vague goals such as "improve lifecycle handling" with an outcome such as "Operators can delete a site with confirmation and a backup by default." Leave out any row kind with nothing to say.
- Every row comes from something the user said or decided, or from what the diff plainly does.

## Confirm

Ask in a plain chat message, never with a question tool such as AskUserQuestion: its dialog cuts the table up and hides most of the text.

- **prod**: show the intent, then end the turn with one line: `Reply "ok", or edit by row number: "2: <new text>", "drop 4", "add must not: <text>".` Wait for the answer.
- **wip**: show the intent and continue.

**Done** when the intent is written, and in prod, confirmed.
