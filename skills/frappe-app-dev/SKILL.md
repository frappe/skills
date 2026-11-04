---
name: frappe-app-dev
description: >-
  Conventions and gotchas for Frappe apps, and running them with Pilot. Use when
  writing or reviewing Frappe code (DocTypes, controllers, whitelisted APIs,
  permissions, background jobs, hooks, frappe.db queries, tests), or when
  creating a bench or site, running migrate, or checking out a PR to get a test
  site ready.
---

# Frappe app development

The Frappe source in `apps/frappe` is the reference for signatures, hook names, and lifecycle order. This file holds what the source does not say.

## Pilot

[Pilot](https://github.com/frappe/pilot) replaces `bench` for development. Frappe commands run through it:

```sh
pilot -b BENCH frappe --site SITE migrate   # was: bench --site SITE migrate
```

- On a classic bench without Pilot, the same Frappe commands run as `bench --site SITE ...`.
- Inside an app checkout that has a dev bench, leave out `-b`.
- Always pass `--site`. A bench's default site can be a different site from the one you mean.
- `pilot ls` shows the Admin panel address, not the site, and marks a bench running under `pilot dev start` as stopped. The site port is `http_port` in `bench.toml`, and `pilot dev info` prints the full site URL.

Choose the bench type by what you are changing:

- **One app**: `pilot dev setup` in its checkout. The checkout stays yours and is linked into `apps/`. The bench is `dev-<folder>` and the site is `dev-<folder>.localhost`, with `Administrator` / `admin` and developer mode on.
- **Frappe itself, or several apps together**: `pilot new NAME --frappe-branch BRANCH`, `pilot -b NAME init`, then `pilot -b NAME new-site`. `pilot dev` refuses the Frappe repository. `pilot new` defaults to `version-16` and MariaDB, while `pilot dev setup` defaults to `develop` and SQLite.

### Check out a PR and get a test site ready

```sh
cd <app checkout>
git fetch origin
git worktree add --detach ../<app>-pr<N> origin/<default branch>
cd ../<app>-pr<N>
gh pr checkout <N> --detach
gh pr view <N> --json baseRefName   # base is version-N? add --frappe-branch version-N below
pilot dev setup                     # about 4 minutes the first time
systemd-run --user --unit=dev-<app>-pr<N> --collect -p WorkingDirectory=$PWD --setenv=PATH=$PATH pilot dev start
pilot dev info
```

The site is ready when `/api/method/ping` on the `pilot dev info` URL returns `pong` and you can log in as `Administrator` / `admin`. Report the URL and the login.

Why it is done this way:

- The worktree leaves the main checkout and its bench untouched. Its folder name gives the bench its name.
- `pilot dev start` stays in the foreground and would die with the agent session, so it runs as a systemd user unit. Without systemd, use another way to keep it running after the session ends.
- A detached checkout always gets Frappe `develop`. The Frappe branch and the database are fixed once the bench exists, so a wrong choice means `pilot dev drop`.
- SQLite is the default. Pass `--database mariadb` when the PR touches raw SQL or database-specific behavior.

To open a site on a remote machine, forward the port. Browsers resolve every `*.localhost` name to the local machine, so the site URL then works unchanged:

```sh
ssh -f -N -L <port>:127.0.0.1:<port> <host>
```

Behind a tunnel or proxy, Frappe picks the site from the hostname, so add an alias in the bench's `sites/` folder: `ln -s <site> <public hostname>`. Without it, requests return 404. Remove the alias before you drop the site. Pilot's `docs/development-proxies.md` covers `host_name` for redirects.

After new commits on the PR, run `pilot dev setup` again. It installs requirements, migrates, and rebuilds. Pilot never pulls or switches branches in a linked app.

To remove the test site:

```sh
systemctl --user stop dev-<app>-pr<N>
pilot --yes dev drop
cd <app checkout> && git worktree remove --force ../<app>-pr<N>
```

### Pilot gotchas

- `pilot dev start` on a frappe-ui app regenerates `frontend/src/types/doctypes.ts`. Keep that file out of commits unless the change is intended.
- On recent Frappe, one `frappe.runner` process runs web, realtime, jobs, and the scheduler. `pilot frappe doctor` then reports `Workers online: 0`, which is normal. Without `frappe.runner`, a development bench may have no scheduler process, so check `pilot processes ls`.
- Vite logs `Could not run 'bench list-app-sites': spawn bench ENOENT`. The API proxy still works, so ignore it.
- A linked app's real path is outside the bench, so relative paths from the app to the bench break:
  - frappe-ui must be new enough to read `FRAPPE_BENCH_PATH`, or the frontend build fails.
  - Node realtime handlers that require `../../frappe/...` need `NODE_PRESERVE_SYMLINKS=1`.
- Ports differ per bench. Read them from `bench.toml` rather than assuming 8000 and 9000.
- Ask before you drop a site or bench you did not create.

## DocTypes

- A hand-written DocType needs `<name>.json` and `<name>.py` with its controller class. With the JSON alone, `migrate` fails with `Module import failed`. Frappe does not create the folder or the controller for you.
- Leave out `creation`, `modified`, `owner`, `modified_by`, and `docstatus`. Frappe adds them.
- Child DocTypes (`istable`) take no permissions. They inherit from the parent.

## Controllers and hooks

- Change validated fields and status through `doc.save()`. `frappe.db.set_value` skips validation and every lifecycle hook, so keep it for counters, timestamps, and cached values.
- `on_update` also runs on insert. Put code that must run once in `after_insert`.
- Check permissions inside the controller method, so they hold on every call path. Apply the same style to all mutating methods of a DocType.
- Prefer `doc_events` to `override_doctype_class`. An override must inherit from the original class and call `super()`.

## APIs

- Put logic for one document in a whitelisted controller method, called through `frm.call` or `/api/v2/document/<DocType>/<name>/method/<method>`. Use standalone API files for work across documents or with no document. A wrapper that only fetches a document and calls its method adds nothing.
- `/api/v2/document` already provides CRUD. See `frappe/api/v2.py`. Write custom endpoints only for logic beyond CRUD.
- Type-hint every whitelisted parameter. Frappe validates and casts arguments from the hints. Without them, arguments arrive as untrusted values.
- Declare `methods=[...]` on every whitelisted function. POST, PUT, PATCH, and DELETE commit at the end of the request, and GET does not.
- With `allow_guest=True`, return only the fields guests need. Leave out user emails and internal IDs.

## Database

- `frappe.db.get_all` ignores permissions, and `frappe.db.get_list` applies them. Use `get_list` in user-facing APIs.
- Use `frappe.qb.get_query` for joins, aggregates, OR filters, and child table queries (docs: https://docs.frappe.io/framework/get_query). It defaults to `ignore_permissions=True`, so pass `False` for user-facing queries.
- Prefer `frappe.qb` to `frappe.db.sql`, including for updates. Keep raw SQL for what the builder cannot express, such as CTEs.
- Frappe commits and rolls back for you in requests, jobs, and patches. Call `frappe.db.commit()` only to flush writes mid-script, and use savepoints for a partial rollback.
- Fetch related records in one batch, not in a loop.
- Use `frappe.db.delete` for bulk deletes. Use `frappe.delete_doc` when `on_trash` or `after_delete` must run.

## Permissions

- Keep `ignore_permissions` to server-side background logic.
- Pair `permission_query_conditions` (filters lists) with `has_permission` (guards one document). Either one alone leaves a gap.
- Build query conditions with `frappe.db.escape`, since they are raw SQL fragments.

## Jobs, cache, and realtime

- Jobs run apart from the request and share no state with it, so pass data as arguments.
- Use `enqueue_after_commit=True` when a job reads data written in the current request. Prefer `frappe.enqueue_doc` when the job is a controller method.
- `frappe.cache` prefixes keys with the site, so pass logical keys. `get_keys` returns the prefixed keys: count them, but do not compare them with logical keys. Redis is not for large objects.
- Use `after_commit=True` on `publish_realtime` during saves. A site-wide broadcast reaches Desk users only, not guests or portal users.

## Frontend

Load the `frappe-ui` skill from the frappe/frappe-ui repository before styling a Vue frontend. Desk forms and lists are generated from the DocType, so add client scripts only for behavior the DocType cannot express.

## Tests

- Tests need `pilot frappe --site SITE set-config allow_tests true` on the site.
- Tests create and delete data, so run them on a separate site from the one in use. A throwaway PR site is fine.
- `IntegrationTestCase` rolls back after each test, so tests need no cleanup. Use `UnitTestCase` for logic with no database. Both are in `frappe.tests`. Test files must be named `test_*.py`.
- If tests fail with `DocType not found`, migrate the test site first.
