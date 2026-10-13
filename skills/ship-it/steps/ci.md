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
   - A real failure → a fixer subagent, then commit and push (step 7 of [SKILL.md](../SKILL.md)). Up to 3 attempts, then ask the user.

## Bot loop (prod)

### Find the review bots

A review bot is a GitHub App or bot account that reviews PRs in this repo. Find them before round 1:

- Read the repo's `AGENTS.md`, `CONTRIBUTING.md`, and `.github/workflows/` for review bots and how to start one.
- Read the comments on the last 5 merged PRs. Note each bot login (the REST API shows `user.type: "Bot"`) that posted findings, not only status or coverage.
- For each bot, note how it starts a review: on every push, or only when a comment asks for it. Take the exact comment text from the docs or an earlier PR.

No review bots → skip the bot loop.

Bots post top-level comments (`issues/<n>/comments`), inline comments (`pulls/<n>/comments`), and reviews (`pulls/<n>/reviews`). Read all three.

### Round

1. Read the comments that already exist before waiting.
2. Right after the push, watch, with one `--bot` per review bot:
   ```bash
   bash <this skill's directory>/scripts/watch-pr.sh <n> --bot <login> [--bot <login> ...] [--trigger "<comment>" ...]
   ```
   Pass one `--trigger` for each bot that reviews only when asked. The script posts each comment once, before it watches. Exit 0 = every bot posted after the push and then went quiet, 2 = timeout, 3 = query failed.
3. Triage every bot finding as **fix**, **decline**, or **ask**:
   - Grade it with the severities in [review/verdict.md](../review/verdict.md): blocker, issue, or nit.
   - Fix blockers and issues that hold up. Fix a nit when it is cheap and in a file the PR touches. Otherwise, decline it.
   - Decline with a one-line reason when the finding contradicts the intent or a recorded decision, is pre-existing code outside the diff, or asks to contort code for the bot.
   - Ask the user (one batched message) when the finding challenges the intent or product behavior.
4. Close the round, in this order:
   - Commit and push the fixes.
   - Reply on each inline thread: what was fixed, or why it was declined.
   - Post the round comment ([review/verdict.md](../review/verdict.md)): every bot finding with its outcome. A top-level comment reaches every bot, including those that skip inline threads.
   - Update the PR body's `## Review` section: decisions and follow-ups.
   - Watch again, right after the push.

Replies and the round comment carry plain text only, so no bot reads them as a command. Only `--trigger` posts commands, each as its own comment.

### Stop

Stop when the latest round of every bot reports nothing you accepted as a blocker or issue, or when the round limit in [review/verdict.md](../review/verdict.md#rounds) stops the loop.

**Done** when CI is green on the final head, the `## Review` marker names that head (see "Pipeline" in [SKILL.md](../SKILL.md)), and the bot loop has stopped. Read the comments one last time, then report: the verdict per bot, what was fixed and declined, the commits pushed, and anything open. Ask the user to review and merge.
