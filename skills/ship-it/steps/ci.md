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
2. Watch, with one `--bot` per review bot. Pass the time of the last push as `--since`:

   ```bash
   bash <this skill's directory>/scripts/watch-pr.sh <n> --bot <login> [--bot <login> ...] [--trigger "<comment>" ...] --since <push time>
   ```

   Note the push time with `date -u +%Y-%m-%dT%H:%M:%SZ` right after each push. When this run did not push, use the time GitHub first saw the head commit: `gh api repos/{owner}/{repo}/commits/<head sha>/check-suites --jq '[.check_suites[].created_at] | min'`. When that prints `null`, nothing records when the head was pushed. Read each bot's latest comment or review. A bot that already reviewed the head sha is done for this round. Watch the others without `--since`, so the watch starts now.

   Pass one `--trigger` for each bot that reviews only when asked. The script posts each comment once, before it watches. `since` stays the push time. Exit 0 = every bot posted after `since` and then went quiet, 2 = timeout, 3 = query failed. The watcher exits 2 at 30 minutes after `since`.

   A bot can post a placeholder first and edit its findings in later. After exit 0, read each bot's latest comment. When one says its review is still running, watch again with only that bot. Pass the `--since` and `--timeout` that the previous run printed, and do not pass `--trigger` again. That `--since` is when the previous run ended, so the replies it already counted do not end the new watch, and that `--timeout` keeps the deadline at 30 minutes after the push.

   After exit 2, read the comments. A bot that still says its review is running, or has not posted, did not finish. List it under **Unfinished bot reviews** in the PR body's `## Review` section ([steps/pr.md](pr.md)). Continue with the findings you have.

3. Write each bot finding as a finding in the [review/verdict.md](../review/verdict.md) format: id `b<n>`, the bot's login as `reviewer`, and verdict.md's severity and action. Its Rounds rules apply too. Use action `no-op` with the outcome `declined: <reason>` when the finding contradicts a recorded decision or asks to contort the code only to satisfy the bot.
4. Run steps 1 to 3 of the Fix loop in [steps/review.md](review.md) on these findings: the fixer subagent for `auto-fix`, one batched message for `ask-user`.
5. Close the round, in this order:
   - Push the fixes (step 7 of [SKILL.md](../SKILL.md)).
   - Reply on each inline thread: what was fixed, or why it was declined.
   - Post the round comment (Fix loop step 4) with every bot finding and its outcome. A top-level comment reaches every bot, including those that skip inline threads.
   - Update the PR body's `## Review` section: decisions, follow-ups, and unfinished bot reviews.
   - Start the next round. Watching the bots again replaces the Fix loop's re-review with new subagents.

Replies and the round comment carry plain text only, so no bot reads them as a command. Only `--trigger` posts commands, each as its own comment.

### Stop

Stop when the latest round of every bot reports nothing you accepted as a blocker or issue, or when the round limit in [review/verdict.md](../review/verdict.md#rounds) stops the loop.

**Done** when CI is green on the final head, the `## Review` marker names that head (see "Pipeline" in [SKILL.md](../SKILL.md)), and the bot loop has stopped. Read the comments one last time, then report: the verdict per bot, what was fixed and declined, the commits pushed, and anything open. Ask the user to review and merge.
