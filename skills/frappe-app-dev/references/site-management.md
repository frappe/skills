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
# Pilot
pilot -b <bench> list-site-apps <site>

# Bench
bench --site <site> list-apps
```

If multiple sites exist, check each until you find the one with the target app installed.

## Creating a new site

Pilot reads the configured database credentials:

```bash
pilot -b <bench> new-site <name>.localhost --admin-password admin
```

For Bench, first check `root_password` in `sites/common_site_config.json`. If it is missing, set it once:

```bash
bench set-config -g root_password '<pwd>'
```

Then create the site. You can also pass the root password without storing it:

```bash
# If root_password is in common_site_config.json
bench new-site <name>.localhost --admin-password admin

# Otherwise, pass it explicitly
bench new-site <name>.localhost --db-root-password '<pwd>' --admin-password admin
```

Naming convention: `<app-name>.localhost` (e.g. `expense_tracker.localhost`).

## Other site commands

See [pilot-operations.md](./pilot-operations.md) or [bench-operations.md](./bench-operations.md). Ask the user before you drop a site.

## Site config

Per-site config lives in `sites/<site>/site_config.json`. Pilot config lives in `bench.toml`. Shared Frappe config lives in `sites/common_site_config.json`.
