# Pilot CLI Reference

Use these commands only when the bench root contains `bench.toml`. Read `<bench>` from `[bench].name` in that file.

Always pass `-b <bench>`. Do not rely on the current directory or single-bench inference.

Pilot commands are not one-for-one Bench replacements. Use native Pilot commands where this reference lists them.

For Frappe commands, use the explicit `pilot -b <bench> frappe ...` passthrough form.

Do not use passthrough for `new-site`, `install-app`, or `uninstall-app`. Pilot must update `bench.toml` for these operations.

## App and site lifecycle

```bash
# New app
pilot -b <bench> new-app <app-name> \
  --title '<title>' \
  --description '<description>' \
  --publisher '<publisher>' \
  --email '<email>' \
  --license '<license>'

# New site
pilot -b <bench> new-site <name>.localhost --admin-password admin

# Install or uninstall an app
pilot -b <bench> install-app <site> <app-name>
pilot -b <bench> uninstall-app <site> <app-name>

# List apps on a site
pilot -b <bench> list-site-apps <site>

# Migrate a site through Frappe
pilot -b <bench> frappe --site <site> migrate

# Set the default site through Frappe
pilot -b <bench> frappe use <site>
```

## Development

```bash
# Start development processes in the background
pilot -b <bench> start

# Enable developer mode through Frappe
pilot -b <bench> frappe set-config -g developer_mode 1

# Open a Python console through Frappe
pilot -b <bench> frappe --site <site> console

# Execute a Python function through Frappe
pilot -b <bench> frappe --site <site> execute frappe.utils.get_url

# Execute a function with arguments through Frappe
pilot -b <bench> frappe --site <site> execute path.to.function arg1 arg2 --kwarg1 hello

# Run tests through Frappe
pilot -b <bench> frappe --site <site> run-tests --app <app-name>
pilot -b <bench> frappe --site <site> run-tests --doctype "DocType Name"

# Build frontend assets with Pilot
pilot -b <bench> build --apps <app-name> --force

# Watch frontend assets through Frappe
pilot -b <bench> frappe watch
```

`pilot -b <bench> start` runs the Frappe asset watcher for development benches.

`pilot -b <bench> uninstall-app` drops the app data. It removes the app when no other site uses it.

## Site maintenance

```bash
# Backup
pilot -b <bench> frappe --site <site> backup

# Restore
pilot -b <bench> frappe --site <site> restore <path>

# Clear cache
pilot -b <bench> frappe --site <site> clear-cache
pilot -b <bench> frappe --site <site> clear-website-cache

# Set site config
pilot -b <bench> frappe --site <site> set-config <key> <value>

# Set shared Frappe config
pilot -b <bench> frappe set-config -g <key> <value>

# Open a MariaDB console for debugging
pilot -b <bench> frappe --site <site> mariadb
```

Pilot has no native site-drop CLI command. Use Pilot Admin to drop a site so Pilot also updates `bench.toml`.

## Fixtures

```bash
# Export fixtures defined in hooks.py
pilot -b <bench> frappe --site <site> export-fixtures --app <app-name>
```
