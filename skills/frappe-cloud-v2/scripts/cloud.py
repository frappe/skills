"""Frappe Cloud v2 from a shell: Central (dashboard.frappe.io) creates the VM, Pilot runs its bench.

    python cloud.py login EMAIL                      # emails a 6-digit code
    python cloud.py login EMAIL --code 123456        # signs in; session kept in .cloudv2/
    python cloud.py teams
    python cloud.py options --team TEAM-XXXXX        # regions, image, plans, billing profile
    python cloud.py create --team T --title "Docs" --plan vm-1 [--region mumbai]
    python cloud.py bench --server server-xxxx       # Pilot admin session for the VM
    python cloud.py site --server S --name docs.mumbai.frappe.cloud
    python cloud.py app --server S --site SITE --name builder [--branch master]
    python cloud.py site-key --server S --site SITE  # Administrator API key -> .cloudv2/<site>.json
    python cloud.py login-url --server S --site SITE # one-time Administrator login link for a browser
    python cloud.py task --server S TASK_ID

State lives in ./.cloudv2 (mode 0600): Central cookies and CSRF, Pilot cookies per VM, site keys.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

CENTRAL = "https://dashboard.frappe.io"
STATE = Path(".cloudv2")
FINISHED = {"success", "failed", "cancelled"}


def state_file(name: str) -> Path:
	STATE.mkdir(mode=0o700, exist_ok=True)
	return STATE / name


def save_json(name: str, data: dict) -> None:
	path = state_file(name)
	path.write_text(json.dumps(data, indent=1))
	path.chmod(0o600)


def load_json(name: str) -> dict:
	path = state_file(name)
	return json.loads(path.read_text()) if path.exists() else {}


class Client:
	"""urllib with a persistent cookie jar per host."""

	def __init__(self, base: str, jar_name: str):
		self.base = base.rstrip("/")
		self.jar_path = state_file(jar_name)
		self.jar = http.cookiejar.MozillaCookieJar(str(self.jar_path))
		if self.jar_path.exists():
			self.jar.load(ignore_discard=True, ignore_expires=True)
		self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
		self.headers: dict[str, str] = {}
		self.reauthenticate = None  # called once on a 401, then the request is retried

	def request(self, method: str, path: str, payload=None, headers=None, raw=False, retried=False):
		url = path if path.startswith("http") else self.base + path
		data = json.dumps(payload).encode() if payload is not None else None
		request = urllib.request.Request(url, data=data, method=method)
		for key, value in {**self.headers, **(headers or {})}.items():
			request.add_header(key, value)
		if data is not None:
			request.add_header("Content-Type", "application/json")
		try:
			with self.opener.open(request, timeout=120) as response:
				body = response.read()
		except urllib.error.HTTPError as error:
			body = error.read()
			self.save()
			if error.code == 401 and self.reauthenticate and not retried:
				self.reauthenticate()
				return self.request(method, path, payload, headers, raw, retried=True)
			message = body.decode(errors="replace")
			raise SystemExit(f"{method} {url} -> {error.code}: {readable_error(message)}") from None
		self.save()
		return body.decode() if raw else json.loads(body or b"{}")

	def save(self) -> None:
		self.jar.save(ignore_discard=True, ignore_expires=True)
		self.jar_path.chmod(0o600)


def readable_error(message: str) -> str:
	try:
		data = json.loads(message)
	except ValueError:
		return message[:500]
	for server_message in json.loads(data.get("_server_messages") or "[]"):
		inner = json.loads(server_message)
		action = inner.get("action_error") or {}
		return action.get("message") or inner.get("message", "")[:500]
	return str(data.get("exception") or data.get("error") or data)[:500]


# ---------------------------------------------------------------- Central


def central() -> Client:
	client = Client(CENTRAL, "central.cookies")
	csrf = load_json("central.json").get("csrf")
	if csrf:
		client.headers["X-Frappe-CSRF-Token"] = csrf
	return client


def method(client: Client, verb: str, name: str, **params):
	"""Central whitelists each method for GET or POST only; the wrong verb answers 'Not permitted'."""
	if verb == "GET":
		query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
		return client.request("GET", f"/api/method/{name}?{query}").get("message")
	return client.request("POST", f"/api/method/{name}", params).get("message")


def cmd_login(args) -> None:
	client = central()
	if not args.code:
		print(method(client, "POST", "central.api.auth.send_code", email=args.email)["message"])
		print("Ask the user for the 6-digit code, then run: cloud.py login", args.email, "--code CODE")
		return
	result = method(client, "POST", "central.api.auth.verify_code", email=args.email, code=args.code)
	if "csrf_token" not in result:
		sys.exit(f"sign-in incomplete: {result}")
	save_json("central.json", {"email": args.email, "csrf": result["csrf_token"]})
	print("signed in as", result["user"])


def cmd_teams(args) -> None:
	for team in method(central(), "GET", "central.api.identity.my_teams"):
		print(f"{team['name']}\t{team['label']}\trole={team['role']}\tmembers={team['members']}")


def newest_pilot_image(client: Client, team: str, region: str) -> dict:
	"""The Server picker's choice: the newest available Frappe (pilot) build without a baked site."""
	images = method(client, "GET", "central.api.images.list_images", team=team, region=region, offering="pilot", flow="Server")["items"]
	bench_only = [image for image in images if image["tags"].get("has_site") == "0" and image["status"] == "available"]
	return max(bench_only, key=lambda image: image["created_at"])


def cmd_options(args) -> None:
	client = central()
	regions = method(client, "GET", "central.api.servers.list_instances", team=args.team)
	print("regions:", ", ".join(f"{r['region']} ({r['display_name']})" for r in regions if r["status"] == "Active"))
	region = args.region or regions[0]["region"]
	image = newest_pilot_image(client, args.team, region)
	print(f"image: {image['id']} {image['title']} frappe={image['tags'].get('frappe_version')} pilot={image['tags'].get('pilot_version')}")
	plans = method(client, "GET", "central.api.images.eligible_plans", team=args.team, region=region, offering="pilot", image_id=image["id"])
	print(f"spend: {plans['current_spend']} of {plans['max_spend']} {plans['currency']} (tier {plans['tier']})")
	for category, rows in plans["plans"].items():
		for row in rows:
			print(f"  {row['plan']:<12} {row['title']:<22} {row['rate']} {row['currency']}/{row['billing_cycle']}  [{category}]")
	profile = method(client, "GET", "central.billing.api.dashboard.account.get_billing_profile", team=args.team)
	if profile.get("complete"):
		print("billing profile: complete; payment method required:", bool(profile.get("payment_method_required")))
	else:
		print("billing profile INCOMPLETE, missing:", ", ".join(profile.get("missing") or []),
			"-> the owner fills it at", CENTRAL + "/dashboard/billing (Add billing details); no card needed unless required")


def cmd_create(args) -> None:
	client = central()
	region = args.region or method(client, "GET", "central.api.servers.list_instances", team=args.team)[0]["region"]
	image = args.image or newest_pilot_image(client, args.team, region)["id"]
	keys = load_json("requests.json")
	request_key = keys.setdefault(f"{args.team}:{args.title}", str(uuid.uuid4()))  # retries stay idempotent
	save_json("requests.json", keys)
	action = method(
		client, "POST", "central.api.servers.create_server", team=args.team, region=region, title=args.title,
		request_key=request_key, plan=args.plan, offering="pilot", image_id=image, hostname=args.hostname,
	)  # fmt: skip
	print("queued", action["action"])
	while action["status"] not in ("Succeeded", "Failed"):
		time.sleep(10)
		action = method(client, "GET", "central.api.servers.action_status", name=action["action"])
		print(" ", action["status"])
	if action["status"] == "Failed":
		sys.exit(f"creation failed: {action.get('error')}")
	server = action["resource_id"]
	for _ in range(60):
		overview = method(client, "GET", "central.api.servers.server_overview", team=args.team, resource_id=server)["server"]
		if overview["status"] == "Running" and overview.get("gateway_url"):
			break
		time.sleep(10)
	servers = load_json("servers.json")
	servers[server] = {"team": args.team, "gateway": overview["gateway_url"]}
	save_json("servers.json", servers)
	print(f"server {server} running; Pilot admin at {overview['gateway_url']}")
	print(f"site names: anything under .{urllib.parse.urlparse(overview['gateway_url']).hostname.split('.', 1)[1]}")


# ---------------------------------------------------------------- Pilot


def pilot(server: str) -> Client:
	"""A Pilot admin client. Its session expires within hours, so a 401 reopens it through Central."""
	saved = load_json("servers.json").get(server)
	if not saved:
		open_bench(server)
		saved = load_json("servers.json")[server]
	client = Client(saved["gateway"], f"pilot-{server}.cookies")
	client.reauthenticate = lambda: open_bench(server, client)
	return client


def open_bench(server: str, client: Client | None = None) -> dict:
	# get_bench_link is GET-only; a POST answers "Not permitted".
	url = method(central(), "GET", "central.api.sso.get_bench_link", server=server)["url"]
	parsed = urllib.parse.urlparse(url)
	servers = load_json("servers.json")
	servers.setdefault(server, {})["gateway"] = f"{parsed.scheme}://{parsed.netloc}"
	save_json("servers.json", servers)
	client = client or Client(servers[server]["gateway"], f"pilot-{server}.cookies")
	sid = urllib.parse.parse_qs(parsed.query)["sid"][0]
	return client.request("POST", "/api/v1/auth/session", {"sid": sid}, retried=True)


def cmd_bench(args) -> None:
	print(open_bench(args.server))


def wait_task(client: Client, task: dict) -> dict:
	task_id = task["task_id"]
	while task.get("status") not in FINISHED:
		time.sleep(10)
		task = client.request("GET", f"/api/v1/tasks/{task_id}")
		print(f"  {task_id} {task['status']}")
	if task["status"] != "success":
		output = client.request("GET", f"/api/v1/tasks/{task_id}/output/content", raw=True)
		sys.exit(f"task {task_id} {task['status']}:\n{output[-3000:]}")
	return task


def cmd_site(args) -> None:
	client = pilot(args.server)
	task = client.request("POST", "/api/v1/sites", {"name": args.name, "apps": []}, headers={"Idempotency-Key": f"site-{args.name}"})
	wait_task(client, task)
	print("site", args.name, "created")


def cmd_app(args) -> None:
	"""Fetch a marketplace app onto the bench, optionally move it to a branch head, install it.
	The marketplace pins a commit; when that commit fails to install (Builder's does on Frappe
	develop), pass --branch so the app is at the branch head before the site install runs."""
	client = pilot(args.server)
	apps = {app["name"]: app for app in client.request("GET", "/api/v1/apps")}
	if args.name not in apps:
		wait_task(client, client.request("POST", "/api/v1/apps", {"name": args.name}))
	if args.branch:
		key = f"{args.name}-{args.branch}-{int(time.time())}"
		wait_task(client, client.request("POST", f"/api/v1/apps/{args.name}/actions/switch-branch", {"branch": args.branch}, headers={"Idempotency-Key": key}))
	installed = {app["name"] for app in client.request("GET", f"/api/v1/sites/{args.site}/apps")["apps"]}
	if args.name not in installed:
		wait_task(client, client.request("POST", f"/api/v1/sites/{args.site}/apps", {"app": args.name}))
	unstick(client, args.site)
	app = client.request("GET", f"/api/v1/apps/{args.name}")
	print(f"{args.name} {app['installed_version']} ({app['current_commit']}, {app['branch']}) on {args.site}")


def unstick(client: Client, site: str) -> None:
	"""A failed install can leave web workers with a stale maintenance flag (API answers
	503 SessionStopped while site_config says 0); rewriting the config makes them reload it."""
	client.request("PATCH", f"/api/v1/sites/{site}/configuration", {"maintenance_mode": 0})
	for _ in range(6):
		try:
			with urllib.request.urlopen(f"https://{site}/api/method/ping", timeout=30) as response:
				if b"pong" in response.read():
					return
		except urllib.error.HTTPError:
			pass
		time.sleep(5)
	print(f"warning: https://{site}/api/method/ping does not answer pong yet")


def login_url(args) -> str:
	return pilot(args.server).request("POST", f"/api/v1/sites/{args.site}/login", {})["url"]


def cmd_login_url(args) -> None:
	print(login_url(args))


def cmd_site_key(args) -> None:
	site = Client(f"https://{args.site}", f"site-{args.site}.cookies")
	desk = site.request("GET", login_url(args), raw=True)  # follows the one-time link; sets sid
	match = re.search(r'csrf_token\s*[=:]\s*"([0-9a-f]{20,})"', desk)
	if not match:
		sys.exit("no CSRF token in the desk page; open the login URL in a browser instead")
	keys = site.request("POST", "/api/method/frappe.core.doctype.user.user.generate_keys", {"user": "Administrator"}, headers={"X-Frappe-CSRF-Token": match.group(1)})["message"]
	save_json(f"{args.site}.json", {"site": f"https://{args.site}", "api_key": keys["api_key"], "api_secret": keys["api_secret"]})
	print(f"API key saved to .cloudv2/{args.site}.json (use: Authorization: token <api_key>:<api_secret>)")


def cmd_task(args) -> None:
	client = pilot(args.server)
	task = client.request("GET", f"/api/v1/tasks/{args.task_id}")
	print(task["status"], task.get("failure") or "")
	print(client.request("GET", f"/api/v1/tasks/{args.task_id}/output/content", raw=True)[-3000:])


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	commands = parser.add_subparsers(dest="command", required=True)
	login = commands.add_parser("login")
	login.add_argument("email")
	login.add_argument("--code")
	login.set_defaults(run=cmd_login)
	commands.add_parser("teams").set_defaults(run=cmd_teams)
	options = commands.add_parser("options")
	options.add_argument("--team", required=True)
	options.add_argument("--region")
	options.set_defaults(run=cmd_options)
	create = commands.add_parser("create")
	for flag in ("--team", "--title", "--plan"):
		create.add_argument(flag, required=True)
	create.add_argument("--region")
	create.add_argument("--image")
	create.add_argument("--hostname")
	create.set_defaults(run=cmd_create)
	bench = commands.add_parser("bench")
	bench.add_argument("--server", required=True)
	bench.set_defaults(run=cmd_bench)
	site = commands.add_parser("site")
	site.add_argument("--server", required=True)
	site.add_argument("--name", required=True)
	site.set_defaults(run=cmd_site)
	app = commands.add_parser("app")
	app.add_argument("--server", required=True)
	app.add_argument("--site", required=True)
	app.add_argument("--name", required=True, help="marketplace app name, such as builder")
	app.add_argument("--branch", help="move the app to this branch head before installing")
	app.set_defaults(run=cmd_app)
	for name, run in (("site-key", cmd_site_key), ("login-url", cmd_login_url)):
		command = commands.add_parser(name)
		command.add_argument("--server", required=True)
		command.add_argument("--site", required=True)
		command.set_defaults(run=run)
	task = commands.add_parser("task")
	task.add_argument("--server", required=True)
	task.add_argument("task_id")
	task.set_defaults(run=cmd_task)
	args = parser.parse_args()
	args.run(args)


if __name__ == "__main__":
	main()
