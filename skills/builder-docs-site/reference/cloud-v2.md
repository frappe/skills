# Frappe Cloud v2: Central and Pilot

What `cloud.py` does, for when a step fails. Central (`frappe/central`, served at dashboard.frappe.io) owns teams, billing and server creation; Atlas runs the VMs; Pilot (`frappe/pilot`) runs the bench on each VM and exposes an admin API at the server's `gateway_url`.

## Central

- **Sign-in is email-code only**: `central.api.auth.send_code` then `verify_code` (POST, guest). `verify_code` returns the session's `csrf_token`; send it as `X-Frappe-CSRF-Token` on every POST. Codes are single-use and rate-limited (10 per 10 minutes per email).
- **Verbs matter.** Each method is whitelisted for GET or POST only, and the wrong verb answers a bare "Not permitted". GET: `my_teams`, `servers.list_instances` (regions), `images.list_offerings|list_images|eligible_plans`, `servers.action_status`, `servers.server_overview`, `sso.get_bench_link`, `billing...get_billing_profile`. POST: `servers.create_server`, `start|stop|restart|terminate_server`.
- **Image.** Offering `pilot` ("Frappe") images carry tags; the Server flow takes the newest `has_site=0` build (a bench, no site). `has_site=1` builds are for trials.
- **Creation gate** (`resource_actions.require_payment_method_or_credit`): wallet credit covering the plan's monthly rate is enough; otherwise a complete billing profile (legal name, address line 1, city), plus an active payment method only when Central Settings requires one (`payment_method_required` in the profile). The owner completes the profile at `/dashboard/billing` → Add billing details.
- **create_server** takes `team, region, title, request_key, plan, offering, image_id[, hostname, has_public_ipv4, has_public_ipv6]`. `request_key` makes retries idempotent; `cloud.py` keeps one per team and title. It returns a queued action: poll `action_status(name)` until `Succeeded`, then `server_overview` until `Running` with a `gateway_url` (`https://admin-vm-<label>.<region>.frappe.cloud`).
- **Network.** Without a public IP the VM is reachable only through the regional proxy: any `*.<region>.frappe.cloud` name routes to it, and Pilot registers site names with the domain provider. SSH needs a public IPv4 (billed) or IPv6.

## Pilot (admin API under `/api/v1`)

- **Session:** `get_bench_link` returns `<gateway>/?sid=<jwt>`; POST `/auth/session` with `{"sid"}` sets the session cookie (bench scope).
- **Long work returns a task:** poll `/tasks/<id>` until `success|failed|cancelled`; `/tasks/<id>/output/content` holds the log.
- **Site:** POST `/sites` `{"name", "apps": []}` (send an `Idempotency-Key`).
- **Builder:** the marketplace entry pins an older commit whose `after_install` fails on Frappe develop (it indexes `Web Page View`, now a virtual doctype). Fetch the app (POST `/apps` `{"name": "builder"}`), move it to the branch head (POST `/apps/builder/actions/switch-branch` `{"branch": "master"}`, which rebuilds assets), then install on the site (POST `/sites/<site>/apps` `{"app": "builder"}`).
- **Stale maintenance flag:** after a failed install the site's API can answer `503 SessionStopped` while `site_config` shows `maintenance_mode: 0` (workers hold the old config). PATCH `/sites/<site>/configuration` `{"maintenance_mode": 0}` rewrites the file and they reload it.
- **Not available on Central-managed VMs:** bench restart and other bench management (`bench_management_forbidden`).
- **Site login:** POST `/sites/<site>/login` returns a one-time URL that signs in Administrator. `site-key` follows it, reads the CSRF token from the desk page, and calls `frappe.core.doctype.user.user.generate_keys` (this rotates Administrator's secret).
- **Server scripts** are on by default on Pilot benches (`server_script_enabled` in common config), which the Doc Page data script needs.
