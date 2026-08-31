# Pilot CLI Reference

Use these commands only when the bench root contains `bench.toml`. Read `<bench>` from `[bench].name` in that file.

Always pass `-b <bench>`. Do not rely on the current directory or single-bench inference.

Pilot commands are not one-for-one Bench replacements. Use native Pilot commands where this reference lists them.

Pilot exposes Frappe commands directly after `-b <bench>`. Do not insert a `frappe` subcommand.

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

# Migrate a site
pilot -b <bench> --site <site> migrate

# Set the default site
pilot -b <bench> use <site>
```

## Development

```bash
# Start development processes in the background
pilot -b <bench> start

# Enable developer mode
pilot -b <bench> set-config -g developer_mode 1

# Open a Python console
pilot -b <bench> --site <site> console

# Execute a Python function
pilot -b <bench> --site <site> execute frappe.utils.get_url

# Execute a function with arguments
pilot -b <bench> --site <site> execute path.to.function arg1 arg2 --kwarg1 hello

# Run tests
pilot -b <bench> --site <site> run-tests --app <app-name>
pilot -b <bench> --site <site> run-tests --doctype "DocType Name"

# Build frontend assets with Pilot
pilot -b <bench> build --apps <app-name> --force

# Watch frontend assets
pilot -b <bench> watch
```

`pilot -b <bench> start` runs the Frappe asset watcher for development benches.

`pilot -b <bench> uninstall-app` drops the app data. It removes the app when no other site uses it.

## Site maintenance

```bash
# Backup
pilot -b <bench> --site <site> backup

# Restore
pilot -b <bench> --site <site> restore <path>

# Clear cache
pilot -b <bench> --site <site> clear-cache
pilot -b <bench> --site <site> clear-website-cache

# Set site config
pilot -b <bench> --site <site> set-config <key> <value>

# Set shared Frappe config
pilot -b <bench> set-config -g <key> <value>

# Open a MariaDB console for debugging
pilot -b <bench> --site <site> mariadb

# Drop a site (DESTRUCTIVE)
pilot -b <bench> drop-site <site>
```

## Fixtures

```bash
# Export fixtures defined in hooks.py
pilot -b <bench> --site <site> export-fixtures --app <app-name>
```
