---
name: guard-review
description: Review a change with Guard, and do not push when the review has P0 findings. Run /guard-review to review the current change. Use it also on your own before `git push`, before `gh pr create` pushes a branch, and in the push step of other skills such as ship-it. Use it only when the Guard MCP server is connected (the `start_review` tool).
---

# Review with Guard

Guard is the code reviewer of the team. Its MCP server gives you the team rules, the code graph and the findings of its checks. You do the review with your own model, and Guard keeps the result.

The instructions of the Guard MCP server and the answer of each tool give the workflow of a local review: `start_review`, the upload command, `review_context`, `submit_review`. Follow them. This skill tells you when to review, what to review, and what to do with the result.

## Only with the Guard MCP server

Use this skill only when your tool list has the `start_review` tool of Guard (some agents call it `mcp__guard__start_review`). Without it, do nothing: push as usual, and do not mention Guard. When the user runs `/guard-review` without it, say in one line that the Guard MCP server is not connected.

## When to review

- **The user runs `/guard-review`**, or asks for a Guard review. Review the current change. Do not push after the review unless the user asks.
- **Before a push.** Review before each command that sends commits to a remote: `git push`, `gh pr create` when it pushes the branch, and the push step of other skills.

Before a push, do not review when:

- The push only deletes branches or sends tags.
- You already reviewed the same commit with Guard in this session, with no P0 findings. The same commit means the same sha as the one that you push.
- `start_review` says that Guard has no such repository that you can read. Tell the user in one line, then push. A Guard admin can share the repository with them.

When a Guard tool fails for another reason (the site is down, the token expired), tell the user what failed. Ask before you push without a review.

## What to review

The upload command of `start_review` sends the diff from the merge base to the working tree. That diff includes uncommitted changes and new files.

- `/guard-review`: run the command in the repository. The review covers the commits of the branch and the uncommitted changes.
- Before a push: review the commits that you push, and nothing else.
  - The working tree is clean and you push `HEAD`: run the command in the repository.
  - The working tree has changes, or you push a commit that is not `HEAD`: run the command in a temporary worktree of that commit.

    ```bash
    tmp=$(mktemp -d) && git worktree add --detach "$tmp" <sha>
    # Run the command of start_review in "$tmp". Then:
    git worktree remove "$tmp"
    ```

  - The push sends more than one branch: review each branch.

Pass the URL of the remote that Guard reviews to `start_review`. Usually this is `origin`, or `upstream` in a clone of a fork. When the command finds no merge base, run `git fetch <remote>` and run the command again.

## What to do with the result

`submit_review` answers with `p0`, the count of P0 findings that Guard kept, and a link to the review. Show the findings, most severe first, as `path:line` with the fix, and the link.

- `p0` is 0: before a push, push now. P1 and P2 findings do not stop the push.
- `p0` is more than 0: do not push. This rule is not optional. It applies also when the user asks you to push, or says that a finding is wrong. Fix the findings when the user agrees, commit the fix, and review again before the push. The user can push by hand.

Do not post the review to GitHub (`publish_review`) or ask Guard for a review on GitHub (`request_review`) unless the user asks.
