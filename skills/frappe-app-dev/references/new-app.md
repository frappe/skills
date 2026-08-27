# New App Workflow

Follow these steps in order.

## Step 1: Confirm Pilot bench root

```bash
ls bench.toml apps/ sites/
```
If it succeeds, the Pilot bench is valid. Do not run anything else to verify.

## Step 2: Enable developer mode

```bash
pilot set-config -g developer_mode 1
```

## Step 3: Pick or create site

See [site-management.md](./site-management.md) for finding or creating a site. A working site is a prerequisite for the next steps.

## Step 4: Create app

Ask user for: app name, title, description, publisher, email, license.

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

## Step 5: Install app on site

```bash
pilot install-app <site> <app-name>
```

## Step 6: Build features

Write DocTypes, controllers, hooks, permissions, UI directly in the app module directory created in step 4.

The app structure after `pilot new-app` creates `myapp`:
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
pilot --site <site> migrate
```

**Rules:**
- After migration succeeds, do NOT query the database directly to verify schema changes. The migrate output is the source of truth.

Start Pilot in the background if it is not already running:
```bash
pilot start
```

Get URL:
```bash
pilot --site <site> execute frappe.utils.get_url
```
