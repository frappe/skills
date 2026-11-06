---
name: frappe-app-dev
description: >-
  How to run and change Frappe apps with Pilot. Use before any work in a Frappe
  app (a repository with hooks.py and DocTypes): writing or reviewing code,
  running migrate or tests, or getting a test site for a PR.
---

# Frappe app development

Pilot replaces `bench` for development. Run Frappe commands through it, such as `pilot frappe --site SITE migrate`. Always pass `--site`, because a bench's default site can be a different one.

Code is done when you have run it on the app's site as a user with the right role, and scanned the files you changed (see [Code](#code)). Report the scan result.

## Run the app you are changing

Work in the bench your checkout already uses, and leave other benches and their Python alone. Pilot supports two layouts:

- **Bench with several apps:** the checkout sits in a bench's `apps/` folder, next to `frappe`. Pilot commands run anywhere inside the bench folder use that bench. Here `pilot dev info` reports "no bench yet" and suggests `pilot dev setup`. Ignore that, and use the bench you are in.
- **Bench per app:** the checkout is a standalone repository, and `pilot dev setup` made a bench for it, with the app linked in. In the checkout, `pilot dev info` shows that bench and the site URL. No bench yet? `pilot dev setup` creates one.

Then:

1. Turn off what you do not need. An idle bench uses about 3.8 GB by default, and about 450 MB with both of these:
   - Set `watch_apps_js = false` under `[bench]` in `bench.toml` (2.8 GB), unless you are changing Frappe or Desk bundles.
   - Run `pilot processes disable frappe-flow_server` (200 MB), unless you need Frappe's AI chat.
2. Start the bench: `pilot start` in a bench with several apps, `pilot dev start` in a standalone checkout. Both stay in the foreground, so run them in a way that outlives your session. `migrate`, `execute`, and tests need the Redis they run.
3. Run `pilot frappe --site SITE migrate`. `ls sites` in the bench lists the sites.

While you work:

- `pilot stop` in the bench or checkout stops that bench and leaves other benches running.
- On a frappe-ui app, `pilot dev start` regenerates `frontend/src/types/doctypes.ts`. Keep that file out of commits unless the change is intended.

To set up a new bench for several apps, or to change Frappe itself, run `pilot new NAME --frappe-branch BRANCH`, `pilot -b NAME init`, `pilot -b NAME get-app <repo URL>` for each app, and `pilot -b NAME new-site SITE --apps <apps>`. For one app, `pilot dev setup` in its checkout is quicker. `pilot new` defaults to `version-16` and MariaDB, while `pilot dev setup` defaults to `develop` and SQLite.

## Test site for a PR

Give the PR a bench of its own, so your work stays as it is. Check the PR's base branch first: `gh pr view <N> --json baseRefName`. Frappe `develop` fits a `develop` base. For a `version-N` base, use Frappe `version-N`. Use MariaDB when the PR touches raw SQL, and SQLite otherwise. The Frappe branch and the database are fixed once the bench exists.

**The app runs alone.** Use a bench per app (about 4 minutes):

```sh
cd <app checkout>
git worktree add --detach <WT>       # WT: a new folder outside any bench, such as ~/worktrees/<app>-pr<N>
cd <WT>
gh pr checkout <N> --detach
pilot dev setup                       # add --frappe-branch version-N or --database mariadb if needed
pilot dev info
```

**The app needs other apps, or you work in a bench with several apps.** Make a new bench with all of them (about 6 minutes for one app). Benches live in `benches/` in the Pilot folder, such as `~/pilot/benches/<B>`.

```sh
pilot new <B> --frappe-branch develop --database sqlite   # or version-N, or leave out --database for MariaDB
pilot -b <B> init
pilot -b <B> get-app <repo URL>                     # once for each app the PR's app needs
pilot -b <B> get-app <PR app repo URL> --skip-assets
cd ~/pilot/benches/<B>/apps/<app>
gh pr checkout <N> --detach
pilot -b <B> build --apps <app>
pilot -b <B> new-site <B>.localhost --apps <apps> --admin-password admin
```

Then trim and start the bench as described in [Run the app you are changing](#run-the-app-you-are-changing).

- **Ready:** you can log in, and the app's own page loads in a browser, such as `/g` for Gameplan. `ping` and login pass even when the frontend is missing. Hand over the URL and the login.
- **New commits:** in a bench per app, run `pilot dev setup` again. It installs requirements, migrates, and rebuilds, but never pulls or switches branches in a linked app. In a bench with several apps, run `gh pr checkout <N> --detach` in `apps/<app>`, then `pilot -b <B> build --apps <app>` and `migrate`.
- **Remove:** run `pilot stop` first. In a bench per app, run `pilot --yes dev drop`, then `git worktree remove --force <WT>` from the main checkout. In a bench with several apps, run `pilot -y -b <B> drop-site <site> --no-backup`, then `pilot -y -b <B> drop`. Ask before you drop a site or bench you did not create.

## Serve a site on another hostname

Frappe picks the site from the hostname. Add an alias in the bench's `sites/` folder with `ln -s <site> <hostname>`, or requests return 404. Remove the alias before you drop the site.

Point the hostname at the port that fits the work:

- **Site port** (`http_port` in `bench.toml`): realtime works. A frontend change appears only after a rebuild.
- **Vite port** (the app's `dev` script): a frontend change reaches the page without a reload. Realtime does not connect. The page has no CSRF token, so logged-in POST requests return 400 until you run `pilot frappe --site SITE set-config ignore_csrf 1`. Set it back to 0 when you move to the site port.

## Code

- Give every `@frappe.whitelist` `methods=[...]` and a type hint on every parameter. GET requests do not commit, and hints are how Frappe validates arguments.
- `frappe.qb.get_query` defaults to `ignore_permissions=True`. Pass `False` in user-facing code.
- A `has_permission` hook must return `True` or `False`. Frappe treats `None` as a denial, so return `True` for users the hook does not restrict.

Scan the files you changed with Frappe's rules, which cover type hints, guest access, SQL injection, manual commits, translations, and more:

```sh
R=/tmp/frappe-semgrep-rules
git -C $R pull -q 2>/dev/null || git clone -q --depth 1 https://github.com/frappe/semgrep-rules.git $R
uvx semgrep scan --config $R/rules <files you changed>
```

Fix findings on the lines you changed. Report older findings in those files without fixing them. A clean scan does not cover the `get_query` and `has_permission` points above.

## Tests

```sh
pilot frappe --site SITE set-config allow_tests true
pilot frappe --site SITE run-tests --doctype "My DocType"
```

Subclass `IntegrationTestCase` from `frappe.tests`. It runs against the real database and rolls back after each test, so write tests without mocks. Report the exact command you ran.
