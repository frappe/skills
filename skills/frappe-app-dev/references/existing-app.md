# Existing App Workflow

Use this flow when the user wants to extend, modify, or fix an app that already exists.

## Step 1: Find and confirm bench root

Run the context resolver from the workspace:

```bash
python3 <skill-directory>/scripts/resolve_frappe_context.py
```

If the site is known, pass `--site <site>`. This can select a different Pilot bench from the current workspace.

If it cannot resolve the context, ask the user to select a bench. Use the returned `bench_root` for manager commands.

Keep code edits in the user's workspace. Do not switch to the bench copy when the workspace is an external app checkout.

## Step 2: Locate the app

```bash
ls apps/
```

Find the app directory. Read its module structure:
```bash
ls apps/<app-name>/<app-name>/
```

Each subdirectory under the module is a Frappe module (contains DocTypes, etc.):
```bash
ls apps/<app-name>/<app-name>/<module-name>/
```

Do NOT create a second app with either manager.

## Step 3: Confirm site and app installation

See [site-management.md](./site-management.md) for finding the right site for this app.

Run the context resolver with the selected site before you continue. Use its manager and bench for all later commands.

Verify the app is installed:
```bash
# Pilot
pilot -b <bench> list-site-apps <site>

# Bench
bench --site <site> list-apps
```

If not installed:
```bash
# Pilot
pilot -b <bench> install-app <site> <app-name>

# Bench
bench --site <site> install-app <app-name>
```

## Step 4: Enable developer mode

```bash
# Pilot
pilot -b <bench> set-config -g developer_mode 1

# Bench
bench set-config -g developer_mode 1
```

## Step 5: Build / modify features

Read the app's existing code to understand patterns before making changes. Load only the relevant feature references from the main SKILL.md table.

Key files to read first:
- `apps/<app>/setup.cfg` or `pyproject.toml` — app metadata
- `apps/<app>/<app>/hooks.py` — existing hooks
- `apps/<app>/<app>/<module>/` — existing DocTypes and modules

## Step 6: Migrate and verify

```bash
# Pilot
pilot -b <bench> --site <site> migrate

# Bench
bench --site <site> migrate
```

Same rules as new app — see [new-app.md](./new-app.md#step-7-migrate-and-verify) for migrate rules.
