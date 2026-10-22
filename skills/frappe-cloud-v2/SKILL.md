---
name: frappe-cloud-v2
description: Create and manage Frappe Cloud v2 servers from a shell: sign in to Central (dashboard.frappe.io), create a VM, open its Pilot bench, create a site, install apps such as Builder, and get an Administrator API key. Use when a task needs a Cloud v2 VM or site, or has to drive Central or Pilot without the dashboard.
---

# Frappe Cloud v2

Central (dashboard.frappe.io) owns teams, billing and servers; Atlas runs the VMs; Pilot runs the bench on each VM and serves an admin API at the server's gateway. `scripts/cloud.py` drives both with the Python standard library and keeps state (sessions, keys) in `./.cloudv2`, so run every command from one working directory.

```sh
CLOUD="python3 <this skill's directory>/scripts/cloud.py"
```

When a step fails, read [reference/central-pilot.md](reference/central-pilot.md): it holds the endpoints, the verb each one needs, and the failure modes found so far.

## Steps

### 1. Sign in

```sh
$CLOUD login EMAIL                 # Central emails a 6-digit code
$CLOUD login EMAIL --code CODE
```

Get the code with AskUserQuestion: the user types it under "Other". A private secret card never hands the value back, so it cannot feed the command.

Done when it prints `signed in as <email>`.

### 2. Choose the team and plan

```sh
$CLOUD teams
$CLOUD options --team TEAM         # regions, image, plans with monthly prices, billing profile
```

A VM is billed: confirm the team, region, plan and monthly price with the user. An incomplete billing profile blocks creation; the team owner fills it at dashboard.frappe.io → Billing → Add billing details. A card is needed only when `options` says a payment method is required.

Done when the user approved a team and plan, and `options` reports a complete billing profile for that team.

### 3. Create the server

```sh
$CLOUD create --team TEAM --title "Title" --plan PLAN [--region REGION]
```

Re-running with the same team and title reuses the request key, so a retry never creates a second server.

Done when it prints the server id and its Pilot gateway URL.

### 4. Site and apps

```sh
$CLOUD bench --server SERVER
$CLOUD site --server SERVER --name NAME.REGION.frappe.cloud
$CLOUD app --server SERVER --site SITE --name APP [--branch BRANCH]
```

Any name under the region's domain routes to the VM. For Builder on a Frappe develop bench pass `--branch master`: the marketplace's pinned commit fails to install there. An app fetch plus branch move rebuilds assets and takes several minutes.

Done when `https://SITE/api/method/ping` answers `pong` and `app` printed the installed version for each app.

### 5. Access

```sh
$CLOUD site-key --server SERVER --site SITE    # Administrator API key -> .cloudv2/SITE.json
$CLOUD login-url --server SERVER --site SITE   # one-time Administrator link for a browser
```

`site-key` rotates Administrator's API secret; tell the user if someone else uses it.

Done when a request with `Authorization: token <api_key>:<api_secret>` to `https://SITE/api/method/frappe.auth.get_logged_user` answers `Administrator`.
