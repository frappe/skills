# Pilot CLI Reference

Use these commands only when the bench root contains `bench.toml`. Run them from that directory or one of its descendants.

From outside the bench, add `-b <bench>` after `pilot`. Pilot passes unknown Frappe commands through to the Frappe CLI.

## App and site lifecycle

```bash
# New app
pilot new-app <app-name> \
  --title '<title>' \
  --description '<description>' \
  --publisher '<publisher>' \
  --email '<email>' \
  --license '<license>'

# New site
pilot new-site <name>.localhost --admin-password admin

# Install or uninstall an app
pilot install-app <site> <app-name>
pilot uninstall-app <site> <app-name>

# List apps on a site
pilot list-site-apps <site>

# Migrate a site
pilot --site <site> migrate

# Set the default site
pilot use <site>
```

## Development

```bash
# Start development processes in the background
pilot start

# Enable developer mode
pilot set-config -g developer_mode 1

# Open a Python console with site context
pilot --site <site> console

# Execute a Python function
pilot --site <site> execute frappe.utils.get_url

# Execute a function with arguments
pilot --site <site> execute path.to.function arg1 arg2 --kwarg1 hello

# Run tests
pilot --site <site> run-tests --app <app-name>
pilot --site <site> run-tests --doctype "DocType Name"

# Build frontend assets
pilot build --apps <app-name> --force
```

`pilot start` runs the Frappe asset watcher for development benches.

`pilot uninstall-app` drops the app data. It also removes the app from the bench when no other site uses it.

## Site maintenance

```bash
# Backup
pilot --site <site> backup

# Restore
pilot --site <site> restore <path>

# Clear cache
pilot --site <site> clear-cache
pilot --site <site> clear-website-cache

# Set site config
pilot --site <site> set-config <key> <value>

# Set shared Frappe config
pilot set-config -g <key> <value>

# Open a MariaDB console for debugging
pilot --site <site> mariadb

# Drop a site (DESTRUCTIVE)
pilot drop-site <site> --db-root-password '<pwd>'
```

## Fixtures

```bash
# Export fixtures defined in hooks.py
pilot --site <site> export-fixtures --app <app-name>
```
