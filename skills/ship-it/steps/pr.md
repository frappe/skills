# 8. PR

Write the PR body, then open or update the PR. When the `technical-writing` skill is installed, follow it for the prose.

## Write for a reader switching context

Apply these rules when creating or updating a PR:

- **Title:** a conventional commit line for the whole change. Describe the concrete behavior in plain English. Name the affected action or feature. Prefer "Add a site deletion command" to "Improve site lifecycle handling".
- **Opening paragraph:** put `## Summary` first. Start with a short paragraph that explains when the problem happens, what goes wrong for the user, and how this change solves it. Introduce any technical term needed to understand the problem. Put the checklist, diagrams, and implementation details after this paragraph.

Before publishing, read the title and the Summary paragraph on their own. A reader new to the change must be able to understand the problem and resulting behavior from those two pieces.

## Body

```markdown
## Summary

<problem-and-solution opening paragraph, then one visual>

## Intent

<the confirmed intent, verbatim>

## Evidence

<one entry per scenario from the test step, marked live or untested, with its evidence shown inline>

## Review

<verdict line>, reviewed <short sha>

**Tidy commits:** <each tidy: commit, one line each>
**Decisions:** <each ask-user finding the user skipped, with their reason>
**Follow-ups:** <non-blocking findings left after the review loop>
**Unfinished bot reviews:** <each review bot that did not finish, one per line>
**Declined to judge:** <what the taste reviewer chose not to judge>

<!-- ship-it: reviewed=<full sha> tier=<prod|wip> -->

## Merge Danger

**Door:** <one-way or two-way>

**Blast radius:** <one word>, then what could break for whom
```

- **wip**: Summary, Intent, and Review only.
- Leave out empty lines inside `## Review`.

### Summary visual

After the opening paragraph, add the smallest visual that makes the change clear. Usually one is enough:

- a call tree for a change in control flow
- a component tree for a UI change
- a shallow file tree for a refactor across files
- a Mermaid diagram for interaction between parts
- a `diff` of one of the above when the point is what changed in a shape that already exists

Keep only the calls, files, and states a reviewer needs.

### Evidence

The evidence itself goes in the body. A reviewer reads the PR, not your logs:

```markdown
**1. Minor bump without the label fails** · live

![Verify changesets fails with "Add the release:minor label"](./02-minor-without-label.png)

**2. Picking an option commits before the popover closes** · live

./03-combobox-pick.mp4

**3. Release PR opens after merge** · untested: the workflow first runs on main
```

- Screenshots: `![alt](./<file>)`. Videos: the `./<file>` reference on its own line, which GitHub renders as a player.
- Transcripts: a fenced block with the command and the trimmed output.
- Pass every referenced file to `--attach`.

### Merge Danger

A **two-way door** is cheap to roll back: revert the commit and nothing is lost. A **one-way door** is not: a data migration, a deleted field, a changed public API, a sent email. The **blast radius** is who or what the change can break: other apps, a layout, existing data, mobile users.

## Commands

- Base branch: the repo's default branch (`gh repo view --json defaultBranchRef`) unless the user named another.
- New PR, ready for review, not draft (bots skip drafts):
  ```bash
  gh pr create --base <base> --title "<title>" --body-file <file> \
    --attach '<path>#<alt text>' ...
  ```
  `--attach` (gh 2.101 or later) uploads each file and rewrites its `./<file>` reference in the body to the uploaded URL.
- Existing PR: `gh pr edit <n> --body-file <file> --attach ...`. Keep any text the human wrote in the body. When the PR is a draft, then run `gh pr ready <n>`.
- Check the upload: `gh pr view <n> --json body` has no `./<file>` reference left, and each one became a `github.com/user-attachments/...` URL. When `gh` appended an upload at the end instead of rewriting its reference (possible for videos), move that URL to the reference's place, on its own line, with `gh pr edit --body-file`.
- Then post the saved round comments from step 3, oldest first: `gh pr comment <n> --body-file <round file>`.

**Done** when the PR exists, is not a draft, every live scenario's evidence renders in the body, the body's `ship-it` marker names `HEAD`, and every review round so far has its comment on the PR.
