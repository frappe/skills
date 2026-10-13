# 9. CI and bots

## Waiting

You own the PR until this step is done. Waiting must re-invoke you when something lands:

| Agent       | How to wait                                                                                          |
| ----------- | ---------------------------------------------------------------------------------------------------- |
| T3 Code     | `watch_pull_request`, then end the turn. T3 wakes you on check results, new comments, and conflicts. |
| Claude Code | The Monitor tool with `persistent: true` on the command below.                                       |
| Codex       | Run the command in the foreground with a long timeout.                                               |

When a wait times out or errors, read the PR state directly before you conclude anything.

## CI

1. Wait for every check to finish: `gh pr checks <n> --watch --interval 30`.
2. All green → bots (prod) or done (wip).
3. A repo with no checks at all → note "no CI" in the report and continue. A PR whose checks never start → ask the user.
4. Failures: read the logs with `gh run view <run-id> --log-failed`.
   - A transient failure (network, runner, rate limit) → `gh run rerun <run-id> --failed`, once.
   - A real failure → a fixer subagent, then commit and push (step 7 of [SKILL.md](../SKILL.md)). Up to 3 attempts; then ask the user.

## Bot loop (prod)

The bots are Greptile (every repo that installs it, re-reviews on push) and barista (repos with a `barista-review.yml` workflow, reviews on `/barista review`). Bots post issue comments; read `issues/<n>/comments`, and Greptile's inline findings in `pulls/<n>/comments`. When the repo uses neither bot, skip the bot loop.

### Round

1. Read the comments that already exist before waiting.
2. Watch:
   ```bash
   bash <this skill's directory>/scripts/watch-pr.sh <n> --sha <full head sha> [--trigger]
   ```
   Add `--trigger` from round 2 on: it posts `/barista review` once, in a barista repo only. Exit 0 = round complete, 2 = timeout, 3 = query failed.
3. Triage every bot finding as **fix**, **decline**, or **ask**:
   - Grade it with the severities in [review/verdict.md](../review/verdict.md): blocker, issue, or nit.
   - Fix blockers and issues that hold up. Fix a nit when it is cheap and in a file the PR touches; otherwise decline it.
   - Decline with a one-line reason when the finding contradicts the intent or a recorded decision, is pre-existing code outside the diff, or asks to contort code for the bot.
   - Ask the user (one batched message) when the finding challenges the intent or product behavior.
4. Close the round, in this order:
   - Commit and push the fixes.
   - Reply on each inline thread: what was fixed, or why it was declined.
   - Post the round comment ([review/verdict.md](../review/verdict.md)): every bot finding with its outcome. Barista reads only top-level comments.
   - Update the PR body's `## Review` section: decisions and follow-ups.
   - Watch again with `--trigger` and the new head sha.

Replies and the round comment carry plain text only; the `--trigger` flag alone posts `/barista review`, as its own comment.

### Stop

Stop when the latest round of every bot reports nothing you accepted as a blocker or issue. From round 3 on, only blockers keep the loop going.

**Done** when CI is green on the final head and the bot loop has stopped. Read the comments one last time, then report: the verdict per bot, what was fixed and declined, the commits pushed, and anything open. Ask the user to review and merge.
