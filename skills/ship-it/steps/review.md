# 3. Review

Two reviewers, each a fresh subagent (see "Subagents" in [SKILL.md](../SKILL.md)):

- **Correctness** follows [review/correctness.md](../review/correctness.md). Runs in both tiers. In wip, tell it to report blockers only.
- **Taste** follows [review/taste.md](../review/taste.md). Runs in prod only.

Run them in parallel. When the repo has rules for its review bots (such as a `rules.md` in a bot's config folder), tell both reviewers to read them: repo rules win over the reviewer files.

## Reviewer prompt

Give each reviewer:

- The path of the reviewer file to follow and of [review/verdict.md](../review/verdict.md) for the output format.
- The intent, verbatim.
- The diff range: `<merge-base>..HEAD` on the first review, `<last-reviewed-sha>..HEAD` on a re-review, plus the list of findings still open.
- Every recorded decision, verbatim, with the instruction that decisions are final.
- The tier.

## Fix loop

1. Collect both reviewers' findings and compute the verdict ([review/verdict.md](../review/verdict.md)).
2. Send the `auto-fix` findings to one fresh fixer subagent. Its brief:
   - For each finding, name the invariant it violates and every place in the changed code where that same invariant must hold. Fix all of them in this round.
   - Make the smallest change that restores the invariant. When the finding sits inside a component the intent does not need, remove the component.
   - Taste fixes go in `tidy:` commits, correctness fixes in `fix:` commits.
   - Run one focused check on the changed area (the tests near it), not the full suite.
3. Present the `ask-user` findings to the user in one message (format in [review/ask.md](../review/ask.md)). Apply their answers: fixes go to a fixer subagent, skips become decisions.
4. Close the round with its round comment ([review/verdict.md](../review/verdict.md)): post it on the PR when one exists, otherwise save it for step 8.
5. Re-review with new subagents, scoped to the commits the fixes added plus the findings still open.
6. Repeat up to 3 rounds. After round 3, only blockers keep the loop going; remaining issues and nits go to the PR's `## Review` section as follow-ups.

**Done** when the verdict is Approve or Approve with comments, or round 3 left only non-blockers, or the user approved past the remaining findings. Note the reviewed `HEAD` sha for the PR's `## Review` marker.
