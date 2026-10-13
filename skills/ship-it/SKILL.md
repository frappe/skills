---
name: ship-it
description: Take finished work to a merge-ready PR in one pass - intent, review, live test, docs, lint, PR, and CI. User-invoked only - run /ship-it [wip|prod] ["intent"], or /ship-it on a branch with an open PR to resume or babysit it.
disable-model-invocation: true
---

# Ship it

You own the work from "code is done" to "PR is ready for the human to merge". Run the pipeline in order. Every step answers for its own edits, and the pipeline only moves forward. The human always merges.

## Tier

Read the repo's `AGENTS.md` for a line `Ship tier: prod` or `Ship tier: wip`. An argument (`/ship-it wip`) overrides it for this run. When the line is missing, ask the user once which tier applies and offer to add the line.

- **prod**: a project in production. Every step runs.
- **wip**: a personal or work-in-progress project. Steps marked – are skipped.

## Pipeline

| #   | Step            | prod                | wip                        | Detail                             |
| --- | --------------- | ------------------- | -------------------------- | ---------------------------------- |
| 1   | Intent          | user confirms       | written, not confirmed     | [steps/intent.md](steps/intent.md) |
| 2   | Rebase          | ✓                   | ✓                          | below                              |
| 3   | Review          | correctness + taste | correctness, blockers only | [steps/review.md](steps/review.md) |
| 4   | Test            | ✓                   | –                          | [steps/test.md](steps/test.md)     |
| 5   | Docs            | ✓                   | –                          | below                              |
| 6   | Lint            | ✓                   | ✓                          | below                              |
| 7   | Commit and push | ✓                   | ✓                          | below                              |
| 8   | PR              | full body           | Summary, Intent, Review    | [steps/pr.md](steps/pr.md)         |
| 9   | CI and bots     | CI, then bot loop   | CI only                    | [steps/ci.md](steps/ci.md)         |

Read a step's detail file when you reach that step, not before.

Steps 4 to 9 can add commits after the review: test fixes, docs, lint, CI fixes, and bot fixes. Before step 8 opens or updates the PR, and before you report done, compare `HEAD` with the last reviewed sha. When commits follow it, re-review `<sha>..HEAD` as in [steps/review.md](steps/review.md). Then put the new reviewed sha in the `## Review` marker.

**Done** means: the PR is open and ready (not draft), the `## Review` marker names `HEAD`, CI is green, and in prod the bot loop has stopped by its rule. Report to the user and ask them to review and merge. Stop there.

## Resume

There is no state file. The branch, the commits, and the PR are the record. On every run, find the first unfinished step:

1. No commits ahead of the base branch and no uncommitted changes → nothing to ship; say so.
2. Read the PR for this branch (`gh pr view --json number,body,headRefOid,isDraft`).
   - No PR → start at step 1.
   - The PR body has `## Intent` → that is the intent; skip step 1 unless the user gave a new one.
   - The `<!-- ship-it: reviewed=<sha> tier=<tier> -->` marker in `## Review` names the last reviewed commit. Commits after it (local or pushed) → re-run review on `<sha>..HEAD` only, then continue forward.
3. Unpushed commits → step 7. CI failing or running → step 9. CI green → step 9's bot loop (prod) or done (wip).

Tell the user which step you are resuming from and why, in one line.

## Where it runs

- **In place** when the checkout is a feature branch or worktree and every uncommitted change belongs to this intent.
- **Ask first** when on the default branch, or when uncommitted changes mix this work with other work. Offer to move this work to a new worktree; create one only on a yes.
- **Frappe app inside a bench**: a plain `git worktree` is invisible to the bench. Run in place.

## Subagents

Every reviewer and every fixer is a fresh subagent that never saw this conversation. Its prompt carries everything it needs: the intent, the recorded decisions, the diff range, and the reviewer file to follow. A fixer is never the reviewer that reported the finding, and a re-review is a new subagent.

| Agent                                         | How to start one                                                                               |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Claude Code                                   | The `Agent` tool.                                                                              |
| Codex                                         | `spawn_agent`. Codex spawns only when told to, so spawn explicitly.                            |
| T3 Code (the `t3-code` MCP tools are present) | `delegate_task` with `mode: "wait"`. Pick provider and model from `orchestrator_capabilities`. |

Use the strongest model available for every subagent. When the agent can start a model from a different provider, give the correctness reviewer that model: a second model family catches mistakes the first one shares with the author.

## Findings and the user

Reviewers return findings in the format in [review/verdict.md](review/verdict.md). Fix `auto-fix` findings without asking. Collect every `ask-user` finding from a step and ask the user about them in one message, laid out as in [review/ask.md](review/ask.md). Answers become decisions, which nothing in the run reverses.

## Inline steps

### 2. Rebase

`git fetch origin`, then rebase onto `origin/<base>`. Also take in commits already on `origin/<branch>` that are missing locally. Resolve conflicts in the spirit of both sides and the intent; when a conflict needs a product decision, ask. When the diff against the base is empty after rebase, stop: there is nothing to ship.

### 5. Docs (prod)

Find what the change made stale: README, docs pages, `AGENTS.md`, code comments near the change, examples. Fix each stale fact in its one authoritative place. Report what you could not resolve as an `ask-user` finding.

### 6. Lint

Run the repo's own formatter and linters with their fix modes: look at `package.json` scripts, `pyproject.toml`, `.pre-commit-config.yaml`, and the CI workflow to see what CI will run. Fix what remains, up to 3 attempts. When the repo has no linters configured, skip.

### 7. Commit and push

Commit in logical groups with conventional messages (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`). Improvements from the taste review go in their own `tidy:` commits, separate from behavior changes. Commit messages describe the change only.

Push safely:

- `git fetch origin`, then confirm `origin/<branch>` (when it exists) is an ancestor of `HEAD`. When it is not, the remote has work you have not taken in: go back to step 2.
- After a rebase that rewrote pushed commits, push with `--force-with-lease=<branch>:<sha you fetched>`. Otherwise a plain push.
