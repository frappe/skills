# Site Management

## Finding existing sites

```bash
ls sites/
```

Ignore these entries: `assets`, `apps.txt`, `common_site_config.json`, `currentsite.txt`. Everything else is a site directory.

## Matching a site to an app

Convention: site name often contains the app name (e.g. `gameplan.localhost` for app `gameplan`).

To confirm which apps are on a site:
```bash
pilot list-site-apps <site>
```

If multiple sites exist, check each until you find the one with the target app installed.

## Creating a new site

Pilot reads the configured database credentials. Create the site with:

```bash
pilot new-site <name>.localhost --admin-password admin
```

Naming convention: `<app-name>.localhost` (e.g. `expense_tracker.localhost`).

## Other site commands

See [pilot-operations.md](./pilot-operations.md). Ask the user before you drop a site.

## Site config

Per-site config lives in `sites/<site>/site_config.json`. Pilot bench config lives in `bench.toml`. Shared Frappe config lives in `sites/common_site_config.json`.
