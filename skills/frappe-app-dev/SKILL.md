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
  "create a REST endpoint in Frappe", "run bench migrate", "run pilot migrate",
  or "install an app on a site" — even if they don't explicitly say "Frappe".
---

# Frappe Full-Stack App Builder

## CLI Selection

- Inspect the bench root before running a manager command.
- Honor the user's CLI choice when the bench supports it.
- If `bench.toml` exists, use Pilot.
- Otherwise, if `Procfile`, `apps/`, and `sites/` exist, use Bench.
- If both markers exist and the user gave no choice, prefer Pilot.
- Run only the command form for the selected manager.

## Global Rules

- Use bare `pilot` or `bench`. Do not use a full path.
- Do not run CLI discovery commands or check the Frappe version.
- Do not delegate manager detection to a subagent. Inspect `bench.toml`, `Procfile`, `apps/`, and `sites/` yourself.
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
