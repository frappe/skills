---
name: frappe-app-dev
description: >-
  How to run and change Frappe apps with Pilot. Use before any work in a Frappe
  app (a repository with hooks.py and DocTypes): writing or reviewing code,
  running migrate or tests, or getting a test site for a PR.
---

# Frappe app development

Pilot replaces `bench` for development. Frappe commands run through it, such as `pilot frappe --site SITE migrate`. Always pass `--site`, because a bench's default site can be a different one.

## Run the app you are changing

Every app checkout gets its own bench. Work there, and leave other benches and their Python alone.

```sh
pilot dev info      # in the checkout: bench and site URL. No bench yet? pilot dev setup
pilot dev start     # stays in the foreground, so run it in a way that outlives your session
pilot frappe --site SITE migrate
```

`migrate`, `execute`, and tests need the Redis that `pilot dev start` runs.

Stop a bench with `pilot stop` in its checkout, which leaves other benches running. `pkill -f "pilot dev start"` kills every dev bench on the machine.

`pilot dev start` on a frappe-ui app regenerates `frontend/src/types/doctypes.ts`. Keep that file out of commits unless the change is intended.

Code is done when you have run it on that site, as a user with the right role, and scanned the files you changed as described under [Code](#code). Report the scan result.

To change Frappe itself or several apps together, use `pilot new NAME --frappe-branch BRANCH`, `pilot -b NAME init`, and `pilot -b NAME new-site`. `pilot new` defaults to `version-16` and MariaDB, while `pilot dev setup` defaults to `develop` and SQLite.

An idle bench uses about 3.8 GB by default. Before you start one, turn off what you do not need, which brings it to about 450 MB:

- Set `watch_apps_js = false` under `[bench]` in `bench.toml` (2.8 GB), unless you are changing Frappe or Desk bundles.
- Run `pilot processes disable frappe-flow_server` (200 MB), unless you need Frappe's AI chat.

## Test site for a PR

`pilot dev setup` on a worktree of the PR gives Frappe `develop`, SQLite, and `Administrator` / `admin` in about 4 minutes.

```sh
cd <app checkout>
git fetch origin
git worktree add --detach ../<app>-pr<N> origin/develop
cd ../<app>-pr<N>
gh pr checkout <N> --detach
gh pr view <N> --json baseRefName   # base is version-N? add --frappe-branch version-N below
pilot dev setup
pilot dev info
```

Then start the bench as described above. The Frappe branch and the database are fixed once the bench exists. Pass `--database mariadb` when the PR touches raw SQL.

The site is ready when you can log in and the app's own page loads in a browser, such as `/g` for Gameplan. `ping` and login pass even when the frontend is missing. Hand over the URL and the login.

After new commits, run `pilot dev setup` again. It installs requirements, migrates, and rebuilds. Pilot never pulls or switches branches in a linked app.

To remove the test site, run `pilot stop`, then `pilot --yes dev drop`, then run `git worktree remove --force ../<app>-pr<N>` from the main checkout. Ask before you drop a site or bench you did not create.

## Serve a site on another hostname

Frappe picks the site from the hostname. Add an alias in the bench's `sites/` folder, `ln -s <site> <hostname>`, or requests return 404. Remove the alias before you drop the site.

Point the hostname at the port that fits the work:

- **Site port** (`http_port` in `bench.toml`): realtime works. A frontend change appears only after a rebuild.
- **Vite port** (the app's `dev` script): a frontend change reaches the page without a reload. Realtime does not connect. The page has no CSRF token, so logged-in POST requests return 400 until you run `pilot frappe --site SITE set-config ignore_csrf 1`.

## Code

- Give every `@frappe.whitelist` `methods=[...]` and a type hint on every parameter. GET requests do not commit, and hints are how Frappe validates arguments.
- `frappe.qb.get_query` defaults to `ignore_permissions=True`. Pass `False` in user-facing code.
- A `has_permission` hook must return `True` or `False`. Frappe treats `None` as a denial, so return `True` for users the hook does not restrict.

Check the files you changed with Frappe's rules, which cover type hints, guest access, SQL injection, manual commits, translations, and more:

```sh
git clone --depth 1 https://github.com/frappe/semgrep-rules.git /tmp/frappe-semgrep-rules   # first time only
uvx semgrep scan --config /tmp/frappe-semgrep-rules/rules <files you changed>
```

Name the files, because `--baseline-commit` reports nothing for uncommitted edits. Fix findings on the lines you changed, and report older findings in those files without fixing them. A clean scan does not cover the `get_query` and `has_permission` points above.

## Tests

```sh
pilot frappe --site SITE set-config allow_tests true
pilot frappe --site SITE run-tests --doctype "My DocType"
```

Subclass `IntegrationTestCase` from `frappe.tests`, against the real database, without mocks. It rolls back after each test. Report that exact command.
