#!/usr/bin/env python3
"""Run the scan, verify, check, and report tasks of a deep-app-audit run.

Usage:
    python run_audit.py RUN_DIR --agents AGENTS.json [--jobs 8] [--dry-run]

RUN_DIR must hold setup.json, and site.json when the run has a test site. The coordinator writes
both files (SKILL.md, steps 1 to 4). This script does everything after that, with no model in the
loop: it queues the tasks, runs each one as a fresh agent process, checks each result file,
queues a verifier for each candidate, applies the caps, and starts the report.

The agent is any CLI that takes a prompt and can read files, run commands, and write a file.
AGENTS.json maps each task kind to a command. See agents.example.json.

The script uses the standard library only.
"""

import argparse
import asyncio
import heapq
import itertools
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
PROMPTS = SKILL_DIR / "prompts"

SEVERITIES = ("Critical", "High", "Moderate", "Low")
RANK = {s: i for i, s in enumerate(SEVERITIES)}
VERDICTS = ("confirmed", "rejected", "uncertain")
CHECK_STATUSES = ("pass", "gaps", "fail", "not applicable")
REPORT_MARKER = "<!-- milkshake deep-app-audit"
CANDIDATE_FIELDS = {
	"security": ("title", "severity", "file", "actor", "input", "impact", "proof"),
	"quality": ("title", "severity", "file", "trigger", "failure", "impact", "proof"),
}

# The prompt directories of each id prefix. The id is the prefix and the file id: A02 in
# security/A-authorization/A02-*.md is S-A02.
PROMPT_DIRS = [
	("S-", "security", "[A-L]-*", "scan"),
	("S-", "security", "checks", "check"),
	("Q-", "quality", "B-correctness", "scan"),
	("Q-", "quality", "A-customization", "scan"),
	("Q-", "quality", "checks", "check"),
]


def track_dir(id):
	return "security" if id.startswith("S-") else "quality"


def track_name(id):
	if id.startswith("S-"):
		return "security"
	return "correctness" if id.startswith("Q-B") else "customization"


def list_prompts():
	"""Map each prompt id to its kind and file."""
	prompts = {}
	for prefix, tdir, pattern, kind in PROMPT_DIRS:
		for path in sorted((SKILL_DIR / tdir).glob(f"{pattern}/*.md")):
			if path.name.startswith("_"):
				continue
			prompts[prefix + path.name.split("-", 1)[0]] = (kind, path)
	return prompts


# --- Templates ------------------------------------------------------------------------------
# {{name}} is a value. {{#if name}}...{{else}}...{{/if}} keeps a part when the value is truthy.
# Blocks nest. An unknown name is an error, so a typo in a template stops the run at the start.

TAG = re.compile(r"\{\{(#if \w+|else|/if|\w+)\}\}")


def _parse(parts, i, stop):
	nodes = []
	while i < len(parts):
		text, tag = parts[i]
		if text is not None:
			nodes.append(("text", text))
		elif tag in stop:
			return nodes, i
		elif tag.startswith("#if "):
			then, i = _parse(parts, i + 1, {"else", "/if"})
			other = []
			if i < len(parts) and parts[i][1] == "else":
				other, i = _parse(parts, i + 1, {"/if"})
			if i >= len(parts) or parts[i][1] != "/if":
				raise ValueError(f"unclosed {{{{{tag}}}}}")
			nodes.append(("if", tag[4:], then, other))
		elif tag in ("else", "/if"):
			raise ValueError(f"unexpected {{{{{tag}}}}}")
		else:
			nodes.append(("var", tag))
		i += 1
	if stop:
		raise ValueError("unclosed {{#if}}")
	return nodes, i


def parse_template(text):
	pieces = TAG.split(text)
	parts = [(p, None) if n % 2 == 0 else (None, p) for n, p in enumerate(pieces)]
	return _parse(parts, 0, set())[0]


def names(nodes):
	found = set()
	for node in nodes:
		if node[0] == "var":
			found.add(node[1])
		elif node[0] == "if":
			found |= {node[1]} | names(node[2]) | names(node[3])
	return found


def render(nodes, values):
	out = []
	for node in nodes:
		if node[0] == "text":
			out.append(node[1])
		elif node[0] == "var":
			out.append(str(values[node[1]]))
		else:
			out.append(render(node[2] if values[node[1]] else node[3], values))
	return "".join(out)


# --- Result files ---------------------------------------------------------------------------


def read_json(path):
	try:
		return json.loads(path.read_text()), None
	except FileNotFoundError:
		return None, "the file does not exist"
	except (json.JSONDecodeError, UnicodeDecodeError) as e:
		return None, f"the file is not valid JSON: {e}"


def validate(task, data):
	"""Return the list of problems in a result. An empty list means the task is complete."""
	if not isinstance(data, dict):
		return ["the top level is not a JSON object"]
	problems = []
	if task.kind == "scan":
		if data.get("id") != task.id:
			problems.append(f'"id" must be "{task.id}"')
		if not isinstance(data.get("coverage"), str):
			problems.append('"coverage" must be a string')
		candidates = data.get("candidates")
		if not isinstance(candidates, list):
			return problems + ['"candidates" must be a list']
		for n, c in enumerate(candidates):
			if not isinstance(c, dict):
				problems.append(f"candidate {n} is not an object")
				continue
			missing = [f for f in CANDIDATE_FIELDS[track_dir(task.id)] if not c.get(f)]
			if missing:
				problems.append(f"candidate {n} has no {', '.join(missing)}")
			if c.get("severity") not in SEVERITIES:
				problems.append(f"candidate {n}: severity must be one of {', '.join(SEVERITIES)}")
	elif task.kind == "verify":
		if data.get("verdict") not in VERDICTS:
			problems.append(f'"verdict" must be one of {", ".join(VERDICTS)}')
		if not data.get("reasoning"):
			problems.append('"reasoning" is empty')
		if data.get("verdict") == "confirmed":
			if data.get("severity") not in SEVERITIES:
				problems.append(f'"severity" must be one of {", ".join(SEVERITIES)}')
			if not isinstance(data.get("finding"), dict):
				problems.append('a confirmed verdict needs the "finding" object')
	elif task.kind == "check":
		if data.get("id") != task.id:
			problems.append(f'"id" must be "{task.id}"')
		if data.get("status") not in CHECK_STATUSES:
			problems.append(f'"status" must be one of {", ".join(CHECK_STATUSES)}')
		if not data.get("summary"):
			problems.append('"summary" is empty')
	return problems


class Task:
	def __init__(self, kind, id, prompt_path=None, n=None, severity=None):
		self.kind, self.id, self.prompt_path, self.n, self.severity = kind, id, prompt_path, n, severity
		self.attempts = 0

	@property
	def key(self):
		return f"{self.id}/{self.n}" if self.kind == "verify" else self.id

	@property
	def slug(self):
		return self.key.replace("/", "-")

	def sort_key(self):
		# Verifiers go first: they unblock the report, and the scan that found the candidate is
		# recent, so the site state that it describes is recent too.
		return (0, RANK.get(self.severity, len(RANK))) if self.kind == "verify" else (1, 0)

	def output(self, run):
		if self.kind == "scan":
			return run / "scans" / f"{self.id}.json"
		if self.kind == "check":
			return run / "checks" / f"{self.id}.json"
		if self.kind == "verify":
			return run / "verdicts" / self.id / f"{self.n}.json"
		return run / "report.md"

	def problems(self, run):
		"""Return the list of problems in the result file. An empty list means the task is complete."""
		if self.kind == "report":
			try:
				first = self.output(run).read_text().split("\n", 1)[0]
			except FileNotFoundError:
				return ["the file does not exist"]
			return (
				[] if first.startswith(REPORT_MARKER) else [f"the first line must start with {REPORT_MARKER}"]
			)
		data, err = read_json(self.output(run))
		return [err] if data is None else validate(self, data)

	def result(self, run):
		return not self.problems(run)


# --- The run --------------------------------------------------------------------------------


class Run:
	def __init__(self, args):
		self.args = args
		self.dir = args.run_dir.resolve()
		self.setup, err = read_json(self.dir / "setup.json")
		if self.setup is None:
			sys.exit(f"setup.json: {err}. Do steps 1 to 4 of SKILL.md first.")
		site, _ = read_json(self.dir / "site.json")
		self.site = site if site and site.get("ready") else None
		self.agents = json.loads(args.agents.read_text())
		self.templates = {
			name: parse_template((PROMPTS / f"{name}.md").read_text())
			for name in ("context", "scan", "verify", "check", "report")
		}
		self.prompts = list_prompts()
		self.slots = self._slots()
		self.queue, self.seq = [], itertools.count()
		self.cond = asyncio.Condition()
		self.active = 0
		self.verify_budget = args.max_verifications
		previous, _ = read_json(self.dir / "run.json")
		self.status = (previous or {}).get("tasks", {})
		self.failed = []
		self.site_down = False
		self.ran = 0
		for sub in ("scans", "checks", "verdicts", "logs", "prompts", "tmp"):
			(self.dir / sub).mkdir(exist_ok=True)

	def _slots(self):
		"""One user set for each worker, when site.json has them. A worker changes only its own
		users, so a reset after its task cannot disturb another task."""
		jobs = self.args.jobs
		if not self.site:
			return [None] * jobs
		slots = self.site.get("slots")
		if not slots:
			return [None] * jobs
		if len(slots) < jobs:
			print(
				f"site.json has {len(slots)} user slots, so the run uses {len(slots)} workers",
				file=sys.stderr,
			)
		return list(range(min(jobs, len(slots))))

	def check_commit(self):
		"""Results from two commits must not mix in one report."""
		try:
			head = subprocess.run(
				["git", "-C", self.setup["target"], "rev-parse", "--short", "HEAD"],
				capture_output=True,
				text=True,
				check=True,
			).stdout.strip()
		except (subprocess.CalledProcessError, FileNotFoundError):
			return
		recorded = self.setup.get("commit")
		if recorded and not head.startswith(recorded) and not recorded.startswith(head):
			sys.exit(
				f"The checkout is at {head}, but setup.json records {recorded}. Use a new run directory."
			)

	def selected(self, id):
		a = self.args
		return (not a.only or any(id.startswith(p) for p in a.only)) and not any(
			id.startswith(p) for p in a.skip
		)

	# --- Prompts ---

	def values(self, task, slot):
		s, site = self.setup, self.site or {}
		if slot is not None:
			users = site["slots"][slot]
		else:
			users = site.get("users", [])
		deps = s.get("dependencies") or []
		return {
			"skill_dir": SKILL_DIR,
			"run_dir": self.dir,
			"run_name": self.dir.name,
			"target": s["target"],
			"app": s["app"],
			"commit": s.get("commit") or "unknown",
			"bench": s.get("bench") or "",
			"framework_version": s.get("frameworkVersion") or "unknown",
			"dependencies": ", ".join(f"{d['app']} ({d.get('path') or 'not on the bench'})" for d in deps)
			or "none",
			"inventory": s.get("inventory") if not s.get("inventoryError") else "",
			"semgrep": s.get("semgrep") if not s.get("semgrepError") else "",
			"semgrep_rules": s.get("semgrepRules") or "",
			"app_notes": s.get("notes") or "",
			"site": site.get("site") or "",
			"base_url": site.get("baseUrl") or "",
			"host_header": site.get("hostHeader") or site.get("site") or "",
			"admin_password": site.get("adminPassword") or "",
			"users": "\n".join(
				f"  {u['email']} / {u.get('password', '')} / {u.get('actor', '')}" for u in users
			)
			or "  none",
			"slot": slot is not None,
			"weakens": ", ".join(
				f"{c['key']}={c['value']}" for c in site.get("config", []) if c.get("weakens")
			),
			"site_notes": site.get("notes") or "",
			"task_slug": task.slug,
			"id": task.id,
			"n": task.n if task.n is not None else "",
			"track": track_name(task.id) if task.kind != "report" else "",
			"track_dir": track_dir(task.id) if task.kind != "report" else "",
			"prompt_path": task.prompt_path or "",
			"output": task.output(self.dir),
		}

	def prompt(self, task, slot, problems=None):
		values = self.values(task, slot)
		text = render(self.templates["context"], values) + "\n\n" + render(self.templates[task.kind], values)
		if problems:
			text += (
				f"\n\nAn earlier attempt at this task did not leave a valid {task.output(self.dir)}:\n"
				+ "\n".join(f"- {p}" for p in problems)
				+ "\nDo the task again, and write the file in the format above."
			)
		return text

	# --- Agents ---

	def command(self, task, prompt_file, prompt):
		role = self.agents["roles"].get(task.kind) or self.agents["roles"]["default"]
		profile = self.agents["agents"][role["agent"]]
		fill = {
			"prompt": prompt,
			"prompt_file": str(prompt_file),
			"run_dir": str(self.dir),
			"target": self.setup["target"],
			"bench": self.setup.get("bench") or self.setup["target"],
			"site": (self.site or {}).get("site", ""),
			"skill_dir": str(SKILL_DIR),
			"model": role.get("model", ""),
		}
		argv = []
		for arg in profile["cmd"]:
			# {model_args} marks where the model flags go. It expands to nothing when the role
			# names no model, so the CLI uses its own default.
			if arg == "{model_args}":
				argv += profile.get("modelArgs", []) if role.get("model") else []
			else:
				argv.append(arg)
		argv = [a.format(**fill) for a in argv]
		# The prompt goes on stdin unless the command takes it as an argument or a file.
		stdin = None if any("{prompt" in a for a in profile["cmd"]) else prompt
		return argv, stdin, profile.get("timeout", 3600), profile.get("env", {})

	async def run_agent(self, task, slot, problems):
		prompt = self.prompt(task, slot, problems)
		prompt_file = self.dir / "prompts" / f"{task.slug}.md"
		prompt_file.write_text(prompt)
		argv, stdin, timeout, env = self.command(task, prompt_file, prompt)
		log = self.dir / "logs" / f"{task.slug}.log"
		with log.open("ab") as fh:
			fh.write(f"\n=== {time.strftime('%F %T')} attempt {task.attempts} slot {slot}\n".encode())
			proc = await asyncio.create_subprocess_exec(
				*argv,
				stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
				stdout=fh,
				stderr=fh,
				cwd=self.dir,
				env={**os.environ, **env, "AUDIT_RUN_DIR": str(self.dir), "AUDIT_TASK": task.key},
				# A group of its own, so that a timeout also stops the tools that the agent started.
				start_new_session=True,
			)
			try:
				await asyncio.wait_for(
					proc.communicate(stdin.encode() if stdin is not None else None), timeout
				)
			except asyncio.TimeoutError:
				os.killpg(proc.pid, signal.SIGKILL)
				await proc.wait()
				fh.write(f"\n=== stopped after {timeout}s\n".encode())
		return proc.returncode

	# --- Site ---

	def site_is_up(self):
		if not self.site:
			return True
		request = urllib.request.Request(
			self.site["baseUrl"].rstrip("/") + "/api/method/ping",
			headers={"Host": self.site.get("hostHeader") or self.site["site"], "X-Audit": "milkshake"},
		)
		try:
			with urllib.request.urlopen(request, timeout=20) as response:
				return response.status == 200
		except OSError:
			return False

	async def wait_for_site(self):
		"""A verifier that runs against a dead site reads the errors as evidence. Stop instead."""
		for _ in range(30):
			if await asyncio.to_thread(self.site_is_up):
				return True
			await asyncio.sleep(10)
		self.site_down = True
		return False

	async def reset(self, slot):
		command = (self.site or {}).get("resetCommand")
		if not command:
			return
		command = command.replace("{slot}", "" if slot is None else str(slot))
		proc = await asyncio.create_subprocess_shell(
			command,
			cwd=self.setup.get("bench") or self.dir,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.STDOUT,
		)
		out, _ = await proc.communicate()
		if proc.returncode:
			print(f"  reset of slot {slot} failed: {out.decode(errors='replace')[-300:]}", file=sys.stderr)

	# --- Queue ---

	def push(self, task):
		heapq.heappush(self.queue, (task.sort_key(), next(self.seq), task))

	def fan_out(self, scan):
		"""Queue a verifier for each candidate that the caps keep, most severe first.

		The run-wide cap depends on the order in which scans finish. So the first fan-out records
		the kept candidates in the scan file, and a resumed run reads that record back. Otherwise
		a resume could verify other candidates than the first run did.
		"""
		data, _ = read_json(scan.output(self.dir))
		candidates = data["candidates"]
		kept = data.get("verify")
		if not isinstance(kept, list):
			order = sorted(range(len(candidates)), key=lambda i: RANK[candidates[i]["severity"]])
			kept = order[: max(0, min(self.args.max_candidates, self.verify_budget))]
			data["verify"] = kept
			data["unverified"] = len(candidates) - len(kept)
			scan.output(self.dir).write_text(json.dumps(data, indent=1))
		self.verify_budget -= len(kept)
		for i in kept:
			task = Task("verify", scan.id, scan.prompt_path, n=i, severity=candidates[i]["severity"])
			if not task.result(self.dir):
				self.push(task)

	async def take(self):
		async with self.cond:
			while not self.queue:
				if self.active == 0:
					return None
				await self.cond.wait()
			self.active += 1
			return heapq.heappop(self.queue)[2]

	async def done(self, task, ok):
		async with self.cond:
			if ok and task.kind == "scan":
				self.fan_out(task)
			self.active -= 1
			self.cond.notify_all()

	async def execute(self, task, slot):
		out = task.output(self.dir)
		out.parent.mkdir(parents=True, exist_ok=True)
		problems, started = None, time.time()
		uses_site = self.site and task.kind != "report"
		while task.attempts < self.args.attempts:
			if uses_site and (self.site_down or not await self.wait_for_site()):
				problems = ["the test site stopped answering, so the run stopped"]
				break
			task.attempts += 1
			self.ran += 1
			code = await self.run_agent(task, slot, problems)
			if uses_site:
				await self.reset(slot)
			problems = task.problems(self.dir)
			if not problems:
				break
			if out.exists():
				out.rename(out.with_name(f"{out.name}.attempt{task.attempts}.invalid"))
			problems.append(f"the agent exited with code {code}")
			print(f"  {task.key}: attempt {task.attempts} invalid: {problems[0]}", file=sys.stderr)
		ok = not problems
		self.status[task.key] = {
			"ok": ok,
			"attempts": task.attempts,
			"seconds": round(time.time() - started),
			"problems": problems or [],
		}
		if not ok:
			self.failed.append({"task": task.key, "problems": problems})
		self.save_status()
		return ok

	async def worker(self, slot):
		while (task := await self.take()) is not None:
			ok = False
			try:
				ok = await self.execute(task, slot)
			finally:
				await self.done(task, ok)
			finished = sum(1 for s in self.status.values() if s["ok"])
			print(
				f"{'ok  ' if ok else 'FAIL'} {task.key:<12} done {finished}, queued {len(self.queue)}, running {self.active}",
				flush=True,
			)

	def save_status(self):
		status = {
			"updated": time.strftime("%F %T"),
			"verificationsLeft": self.verify_budget,
			"siteDown": self.site_down,
			"failed": self.failed,
			"tasks": self.status,
		}
		tmp = self.dir / "run.json.tmp"
		tmp.write_text(json.dumps(status, indent=1))
		tmp.replace(self.dir / "run.json")

	def initial_tasks(self):
		ids = [i for i in self.setup["scans"] + self.setup["checks"] if self.selected(i)]
		unknown = [i for i in ids if i not in self.prompts]
		if unknown:
			sys.exit(f"setup.json names ids with no prompt file: {', '.join(unknown)}")
		tasks = []
		for id in ids:
			kind, path = self.prompts[id]
			tasks.append(Task(kind, id, path))
		return tasks

	def summary(self):
		"""The counts for the reply to the user. They come from the files, not from a model."""
		counts = {}
		for path in sorted((self.dir / "verdicts").glob("*/*.json")):
			data, _ = read_json(path)
			if not data:
				continue
			track = track_name(path.parent.name)
			verdict = data.get("verdict", "invalid")
			key = f"{verdict} {data.get('severity')}" if verdict == "confirmed" else verdict
			counts.setdefault(track, {}).setdefault(key, 0)
			counts[track][key] += 1
		unverified = {}
		for path in (self.dir / "scans").glob("*.json"):
			data, _ = read_json(path)
			if data and data.get("unverified"):
				unverified[data.get("id", path.stem)] = data["unverified"]
		return {"verdicts": counts, "unverified": unverified, "failed": self.failed}

	def check_templates(self, tasks):
		known = set(self.values(tasks[0] if tasks else Task("report", "report"), self.slots[0]))
		for name, nodes in self.templates.items():
			unknown = names(nodes) - known
			if unknown:
				sys.exit(f"prompts/{name}.md names unknown values: {', '.join(sorted(unknown))}")

	async def main(self):
		self.check_commit()
		tasks = self.initial_tasks()
		self.check_templates(tasks)
		if self.args.dry_run:
			return self.dry_run(tasks)

		# Scans with a recorded fan-out go first, so the budget that they took is spent before
		# a scan without a record takes its share.
		def recorded(task):
			return (
				task.kind == "scan"
				and task.result(self.dir)
				and "verify" in read_json(task.output(self.dir))[0]
			)

		tasks.sort(key=lambda task: not recorded(task))
		for task in tasks:
			if not task.result(self.dir):
				self.push(task)
			elif task.kind == "scan":
				self.fan_out(task)
		print(f"{len(self.queue)} tasks queued, {len(self.slots)} workers", flush=True)
		await asyncio.gather(*(self.worker(slot) for slot in self.slots))

		report = Task("report", "report")
		if self.site_down:
			print("The test site stopped answering. Fix it, then run this script again.", file=sys.stderr)
		elif not self.args.no_report and (self.ran or not report.result(self.dir)):
			# A report older than the newest result is stale.
			ok = await self.execute(report, None)
			print(f"{'ok  ' if ok else 'FAIL'} report", flush=True)

		summary = self.summary()
		(self.dir / "summary.json").write_text(json.dumps(summary, indent=1))
		print(json.dumps(summary, indent=1))
		return 1 if self.failed or self.site_down else 0

	def dry_run(self, tasks):
		"""Show the queue and one rendered prompt of each kind. Start no agent."""
		shown = set()
		for task in tasks:
			state = "done" if task.result(self.dir) else "queued"
			print(f"{task.kind:<6} {task.id:<8} {state}")
			if task.kind not in shown:
				shown.add(task.kind)
				argv, stdin, _, _ = self.command(task, "<prompt file>", "<prompt>")
				print("  command:", " ".join(argv), "(prompt on stdin)" if stdin else "")
				print("\n".join("  | " + line for line in self.prompt(task, self.slots[0]).splitlines()))
		return 0


def parse_args():
	p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	p.add_argument("run_dir", type=Path)
	p.add_argument("--agents", type=Path, required=True, help="the agent commands, as in agents.example.json")
	p.add_argument("--jobs", type=int, default=8, help="agents that run at the same time")
	p.add_argument("--attempts", type=int, default=2, help="tries for each task")
	p.add_argument("--max-candidates", type=int, default=15, help="verification cap for each scan")
	p.add_argument("--max-verifications", type=int, default=600, help="verification cap for the run")
	p.add_argument("--only", nargs="*", default=[], help="id prefixes to run")
	p.add_argument("--skip", nargs="*", default=[], help="id prefixes to leave out")
	p.add_argument("--no-report", action="store_true", help="stop before the report")
	p.add_argument("--dry-run", action="store_true", help="show the tasks and the prompts, start no agent")
	return p.parse_args()


if __name__ == "__main__":
	sys.exit(asyncio.run(Run(parse_args()).main()))
