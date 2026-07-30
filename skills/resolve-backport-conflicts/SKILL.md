---
name: resolve-backport-conflicts
description: Resolve merge conflicts in a Mergify backport pull request. When a cherry-pick fails, Mergify commits the conflict markers as they are. This skill takes a pull request link or number as an argument.
disable-model-invocation: true
---

## How Mergify leaves the branch

Mergify backports a pull request with a cherry-pick. When the cherry-pick conflicts, Mergify runs `git add` on the conflicted files and commits them unresolved. The branch then holds raw conflict markers:

```
<<<<<<< HEAD
content of the target branch, such as version-16-hotfix
=======
content of the commit under backport
>>>>>>> <sha> (commit subject)
```

The `HEAD` side is the target branch. The `>>>>>>>` side is the pull request under backport. Neither side wins by default.

## Steps

### 1. Check out the pull request

Work inside the repository that owns the pull request. If the current directory is a different repository, clone the correct one into the scratchpad directory.

```bash
gh pr view <pr-url> --json number,title,body,baseRefName,headRefName,headRepositoryOwner,url
gh pr checkout <pr-url> --force
```

The `--force` flag resets a stale local branch to the pull request head. If the working tree is dirty, stop and tell the user. Do not discard the work of the user.

### 2. Read the original pull request

The Mergify description holds the line `This is an automatic backport of pull request #<N>`. Read the number from that line. If the line is absent, read the number from the branch name `mergify/bp/<branch>/pr-<N>`.

```bash
gh pr view <N> --json title,body,url
gh pr diff <N>
```

This diff states the intent of the backport. Read all of it before you edit a file.

### 3. Find every marker

```bash
git grep -nE '^(<{7}|={7}|>{7})' -- . || echo "no markers"
git diff HEAD~1 --stat
git log -1 --format=%s
```

The last command confirms that `HEAD` is the conflict commit of Mergify. Look also for leftover `.rej` and `.orig` files.

### 4. Resolve each conflict

1. Read the code around the conflict until you know what it does on this branch.
2. Start from the target branch side. It shows what the release branch holds today.
3. Apply the change of the original pull request on top of that side.
4. Drop every line that the diff of the original pull request does not contain.
5. Delete the three marker lines.

Step 4 matters most. A conflict hunk drags in unrelated work from later commits on the source branch. Renamed helpers, new APIs, and unrelated refactors arrive this way. None of them belong in a release branch.

If the backport needs a function or a module that the target branch does not have, do not write a replacement. Report the gap and ask the user how to continue.

Mergify also stages clean hunks that belong to other commits. To catch these, compare the whole conflict commit against the diff of the original pull request. Revert the hunks that do not match.

### 5. Verify

```bash
git grep -nE '^(<{7}|={7}|>{7})' -- .
git diff HEAD
```

The first command must print nothing. Read every line that the second command prints. Compare `git diff HEAD~1` against `gh pr diff <N>`. Apart from branch differences, the two diffs must match.

If the repository has a linter or a formatter, run it on the files you changed. While one marker remains, do not continue.

### 6. Commit and push

```bash
git add <modified files>
git commit -m "chore: resolve conflict"
git push <remote> HEAD:<headRefName>
```

To choose the remote, match `headRepositoryOwner` from step 1 against the output of `git remote -v`. A Mergify branch lives on the upstream repository, not on a fork. Never force-push.

### 7. Remove the `conflicts` label

Mergify adds a `conflicts` label when the cherry-pick fails. The label stays until someone removes it. After the push succeeds, and only if no marker remains, remove it:

```bash
gh pr edit <pr-url> --remove-label conflicts
```

The command fails if the pull request does not carry the label. That failure is harmless. If you could not resolve every conflict, leave the label in place.

### 8. Summarize

Report these points to the user:

1. The backport pull request and the original pull request.
2. Each file that held a conflict, with one line on how you resolved it.
3. Each change you dropped as unrelated, with the reason.
4. Each conflict you could not resolve.
5. The sha of the pushed commit.

State the facts. If a resolution is a judgment call, say so.
