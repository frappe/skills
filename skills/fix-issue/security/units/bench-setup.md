# Setting up a bench for one release line

Each release line gets its own bench: every site in a bench runs the same app checkouts, so
switching a branch in one bench changes the code that all its sites see.

## 1. Read the line's requirements from the branch

The Python and Node versions differ between majors, so read them at the branch rather than assuming:

```bash
git -C <frappe-checkout> show "upstream/<frappe-branch>:pyproject.toml" | grep requires-python
git -C <frappe-checkout> show "upstream/<frappe-branch>:package.json" | grep -A2 '"engines"'
git -C <app-checkout> show "upstream/<app-line>:pyproject.toml" | grep -A2 'frappe-dependencies'
```

In October 2026 version-15 needs Python ≥3.10 and Node ≥18, while version-16 and develop need
Python 3.14 and Node ≥24. Re-read these. They change.

The app's `frappe-dependencies` range names the frappe major. Pair `version-N-hotfix` of the app
with frappe's `version-N-hotfix`, and `develop` with frappe's `develop`.

## 2. Create the bench

```bash
bench init --frappe-branch <frappe-branch> --python <python-for-this-line> <bench-dir>
cd <bench-dir>
bench get-app --branch <app-line> <app-repo-url>
# Add any apps listed in the app's required_apps (hooks.py), on their matching branches.
```

Bench clones each app with its remote named `upstream`, which is the scripts' default `REMOTE`. Add
your fork as a second remote for pushing fix branches.

The verification needs full history and tags: the fix differential reads `<sha>~1`, and the release
check reads tags. If the bench was set up with `shallow_clone`, unshallow each app you will verify:

```bash
[ -f apps/<app>/.git/shallow ] && git -C apps/<app> fetch upstream --unshallow --tags
```

## 3. Sites for the two-site regression

Both sites are new. A long-lived site carries customisations nobody remembers, and it passes tests
that a real upgrade fails.

```bash
# fresh: at the fix tip
bench new-site fresh.localhost --install-app <app> --admin-password <pw>
bench --site fresh.localhost set-config developer_mode 1

# pre-patch: install at the base, customise, then upgrade to the fix
git -C apps/<app> switch --detach upstream/<app-line>
bench new-site prepatch.localhost --install-app <app> --admin-password <pw>
#   ... complete setup, seed data, and edit the relevant DocType in Role Permission Manager
#   so that Custom DocPerm rows exist ...
git -C apps/<app> switch <fix-branch>
bench --site prepatch.localhost migrate
```

Use a real `bench migrate`. `reload_doc` skips the patch path that an upgrading site goes through.
Confirm your patch ran by finding its row in `Patch Log`.
