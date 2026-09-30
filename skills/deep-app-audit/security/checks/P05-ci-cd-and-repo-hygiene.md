---
id: P05
---
# P05 — CI/CD and repository hygiene

**Kind:** posture check.

**Applies to:** the repository and its hosting organization, not an app checkout. It needs
that access, so run it separately from a code audit. If you only have the checkout, audit
`.github/` and the build scripts and say what you could not reach.

## Task
- Workflow triggers: `pull_request_target`, `workflow_run`, and `issue_comment` combined with
  checking out or executing PR code — that is arbitrary code execution with repo secrets.
- Secrets referenced in workflows that run on forked PRs.
- Unpinned third-party actions (`@main`, `@v3` floating tag rather than a commit SHA).
- `GITHUB_TOKEN` permissions — default write vs least privilege.
- Self-hosted runners reachable by fork PRs.
- Committed credentials anywhere in git history. Scan the history, not just HEAD.
- Dockerfiles: secrets in build args or layers, running as root, base image freshness.
- Branch protection, required reviews, and who can push to release branches.

## Confirm
- Fork-PR reachability is what turns most of these from theoretical to critical. Check the
  trigger, not just the step. Where you can state the trigger and what an attacker gets, report
  it as a finding, not a checklist row.

## Output
Workflow file, trigger, what an attacker gets.
