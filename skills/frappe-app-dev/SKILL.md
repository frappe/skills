---
name: frappe-app-dev
description: >-
  Builds full-stack Frappe Framework applications end-to-end. Use this skill any
  time the user mentions: creating or modifying a DocType, writing a controller
  or lifecycle hook, adding a whitelisted API, setting up a new Frappe app or
  bench site, building a desk form or list view, creating portal pages, writing
  background jobs or scheduled tasks, managing permissions or roles, writing
  Frappe tests, or working with frappe.db / frappe.qb. Also applies when the
  user says things like "how do I hook into save", "add a field to a DocType",
  "create a REST endpoint in Frappe", "run bench migrate", "run a Pilot site migration",
  or "install an app on a site" — even if they don't explicitly say "Frappe".
---

# Frappe Full-Stack App Builder

## CLI Selection

Run the bundled [context resolver](./scripts/resolve_frappe_context.py) before a manager command.

```bash
python3 <skill-directory>/scripts/resolve_frappe_context.py --site <site>
```

- Pass `--site` for an existing site. The resolver checks every bench in the Pilot installation.
- Omit `--site` for a new site or a bench-only command. Run it from inside the target bench.
- Set `FRAPPE_BENCH_ROOTS` to a path-separated list when a legacy bench is outside the current workspace.
- Use only a result with `"status": "resolved"`.
- Stop and ask the user to select a bench when the result is ambiguous, unavailable, or unresolved.
- Honor an explicit CLI choice only when it matches the resolved site or bench.
- Use the returned `manager` and `bench`. Run only that manager's command form.
- A Pilot site takes priority over an unrelated legacy bench in the current directory.
- If the same site exists in Pilot and Bench, treat it as ambiguous.

## Global Rules

- Use bare `pilot` or `bench`. Do not use a full path.
- Always pass `-b <bench>` to Pilot commands that operate on a bench.
- Do not rely on the current directory or single-bench inference for Pilot.
- Use the exact Pilot syntax in [pilot-operations.md](./references/pilot-operations.md). Do not translate Bench commands mechanically.
- Never run `pilot --site ...`. Use `pilot -b <bench> --site ...`.
- Pilot exposes Frappe commands directly. Do not insert a `frappe` subcommand.
- Do not run manual CLI discovery commands or check the Frappe version. Use the context resolver.
- Do not delegate manager detection to a subagent.
- Do not create DocType folders with `mkdir`. Let the selected manager run the site migration.
- Run the selected manager's development processes in the background only.
- Before starting processes, check if they are already running in an existing terminal.
- Include the site name in every site-specific command. Never run a bare migration.

## Flow Selection

Determine which flow applies, then read ONLY the relevant file:

### Creating a brand new app

Read [new-app.md](./references/new-app.md) — covers bench setup, app scaffolding, site creation, and installation.

### Working on an existing app

Read [existing-app.md](./references/existing-app.md) — covers finding the bench, locating the app, confirming site, and extending features.

## Feature References

Load ONLY the references needed for the current task:

| Topic            | When to load                                 | File                                                    |
| ---------------- | -------------------------------------------- | ------------------------------------------------------- |
| Site management  | Finding/creating/managing sites              | [site-management.md](./references/site-management.md)   |
| DocTypes         | Creating/modifying DocTypes, fields, naming  | [doctypes.md](./references/doctypes.md)                 |
| Controllers      | Document lifecycle, server logic             | [controllers.md](./references/controllers.md)           |
| Whitelisted APIs | REST endpoints, `@frappe.whitelist()`        | [api.md](./references/api.md)                           |
| Database & ORM   | `frappe.db`, queries, raw SQL                | [database.md](./references/database.md)                 |
| Caching          | Redis, `frappe.cache`                        | [caching.md](./references/caching.md)                   |
| Realtime         | WebSocket, `publish_realtime`                | [realtime.md](./references/realtime.md)                 |
| Background jobs  | `frappe.enqueue`, scheduled jobs             | [background-jobs.md](./references/background-jobs.md)   |
| Hooks            | `hooks.py` patterns                          | [hooks.md](./references/hooks.md)                       |
| Permissions      | Roles, DocType permissions, `has_permission` | [permissions.md](./references/permissions.md)           |
| Testing          | Writing & running tests                      | [testing.md](./references/testing.md)                   |
| Frontend & UI    | Desk UI, Vue SPA, portal pages           | [frontend.md](./references/frontend.md) (router → 3 sub-files) |
| Pilot CLI        | Pilot and Frappe passthrough commands        | [pilot-operations.md](./references/pilot-operations.md) |
| Bench CLI        | Bench commands                               | [bench-operations.md](./references/bench-operations.md) |
