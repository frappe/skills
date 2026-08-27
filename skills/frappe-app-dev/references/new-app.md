# New App Workflow

Follow these steps in order.

## Step 1: Confirm bench root

```bash
ls apps/ sites/
```

Use Pilot if `bench.toml` exists. Otherwise, use Bench if `Procfile` exists.

## Step 2: Enable developer mode

```bash
# Pilot
pilot set-config -g developer_mode 1

# Bench
bench set-config -g developer_mode 1
```

## Step 3: Pick or create site

See [site-management.md](./site-management.md) for finding or creating a site. A working site is a prerequisite for the next steps.

## Step 4: Create app

Ask user for: app name, title, description, publisher, email, license.

For Pilot:

```bash
pilot new-app <app-name> \
  --title '<title>' \
  --description '<description>' \
  --publisher '<publisher>' \
  --email '<email>' \
  --license '<license>'
```

Example:

```bash
pilot new-app expense_tracker \
  --title 'Expense Tracker' \
  --description 'Track expenses' \
  --publisher 'John' \
  --email 'john@example.com' \
  --license mit
```

For Bench, pipe the answers with `printf`. Do not use a heredoc, `--no-input`, or `--no-git`.

```bash
printf '<title>\n<description>\n<publisher>\n<email>\n<license>\nN\nN\nN\n' | bench new-app <app-name>
```

Example:

```bash
printf 'Expense Tracker\nTrack expenses\nJohn\njohn@example.com\nmit\nN\nN\nN\n' | bench new-app expense_tracker
```

## Step 5: Install app on site

```bash
# Pilot
pilot install-app <site> <app-name>

# Bench
bench --site <site> install-app <app-name>
```

## Step 6: Build features

Write DocTypes, controllers, hooks, permissions, UI directly in the app module directory created in step 4.

The app structure after the selected manager creates `myapp`:
```
apps/myapp/
  myapp/
    myapp/          ← module directory (same name as app)
      __init__.py
    hooks.py
    __init__.py
  setup.py
```

Load the relevant feature references from the main SKILL.md table as needed.

## Step 7: Migrate and verify

```bash
# Pilot
pilot --site <site> migrate

# Bench
bench --site <site> migrate
```

**Rules:**
- After migration succeeds, do NOT query the database directly to verify schema changes. The migrate output is the source of truth.

Start development processes in the background if they are not already running:
```bash
# Pilot
pilot start

# Bench
bench start
```

Get URL:
```bash
# Pilot
pilot --site <site> execute frappe.utils.get_url

# Bench
bench --site <site> execute frappe.utils.get_url
```
