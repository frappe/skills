# 1. Intent

The intent is the acceptance criteria every later step judges the change against: reviewers, the test step, the PR body, and the review bots. A vague intent makes every later step guess, so write it complete.

## Source

1. The intent the user passed as an argument (`/ship-it "add X; must not change Y"`).
2. Otherwise, the `## Intent` section of this branch's PR.
3. Otherwise, write it from this conversation and the diff: what the user asked for, the decisions made along the way, and what the commits do.

## Format

A reader should understand the intent in one quick read:

```markdown
<One short paragraph in plain words: who this is for, what they can do after the change, and why it matters.>

1. <a behavior the change must have>
2. <another one>
3. Must not: <a behavior the change must leave alone>
```

- The paragraph is the goal. Assume the reader has no context from this conversation. Name the concrete outcome: write "Operators can delete a site, with a confirmation and a backup by default", not "Improve site lifecycle handling". Mention related work left out on purpose in one sentence at the end, when there is any.
- At most 5 numbered items. Each item is one short line. Keep only behaviors a reviewer or tester must check. Leave out file lists, README edits, and other details the diff shows.
- Start an item with "Must not:" for a behavior the change must leave alone or never introduce.
- Keep the numbers stable: scenarios, findings, and replies refer to them (`intent #3`).
- Every item comes from something the user said or decided, or from what the diff plainly does.

## Confirm

Ask in a plain chat message, never with a question tool such as AskUserQuestion: its dialog hides most of the text.

- **prod**: show the intent, then end the turn with one line: `Reply "ok", or edit by item number: "2: <new text>", "drop 3", "add must not: <text>".` Wait for the answer.
- **wip**: show the intent and continue.

**Done** when the intent is written, and in prod, confirmed.
