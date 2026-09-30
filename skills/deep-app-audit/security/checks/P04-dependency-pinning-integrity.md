# P04 — Version pinning and integrity

**Kind:** posture check. It reports which dependencies are not determined by the repo, not which
ones are vulnerable — CVEs belong to `L01` and `L02`.

## Task
- Find unpinned or wildcard ranges (`*`, bare `>=`) in `pyproject.toml` and `package.json`.
- Check whether lockfiles exist, are committed, and are actually used in CI and in the Docker
  build.
- Check hash pinning and integrity fields in the lockfiles.
- List dependencies installed from a git URL, a fork, or a non-default index — each is a
  supply-chain trust decision that should be deliberate.
- Check package names close to a popular package (typosquat check), and any dependency added
  recently with few downloads.
- Find post-install scripts in JS dependencies.

## Confirm
- An unpinned range on a first-party Frappe app is a policy choice; an unpinned range on a
  third-party package is a real risk. Distinguish them.

## Output
One list of dependencies whose exact installed code is not determined by the repo.
