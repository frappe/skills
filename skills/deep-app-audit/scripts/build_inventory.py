"""Static endpoint inventory builder for a Frappe app checkout (read-only).

Usage:
    python build_inventory.py OUTPUT.json [--root APP_CHECKOUT] [--module MODULE_NAME]

`--root` is the app repository checkout (default: current directory). `--module` is the
Python package inside it that holds `hooks.py`; it is detected automatically when omitted.
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

ROOT = ""  # app repository checkout, set from the command line
APP = ""  # the Python package inside ROOT that holds hooks.py
DEST = ""  # output path for the inventory JSON
DEFAULT_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".runs", "dist", "build"}
SKIP_DIRS = set(DEFAULT_SKIP_DIRS)

SINKS = {
	"sql": [r"\bfrappe\.db\.sql\b", r"\bfrappe\.db\.multisql\b", r"\bdb\.sql\b", r"\.sql\(", r"\bfrappe\.qb\b"],
	"get_doc": [r"\bfrappe\.get_doc\b", r"\bfrappe\.get_cached_doc\b", r"\bfrappe\.get_last_doc\b", r"\bfrappe\.new_doc\b", r"\bget_doc\b"],
	"get_list": [r"\bfrappe\.get_all\b", r"\bfrappe\.get_list\b", r"\bfrappe\.db\.get_all\b", r"\bfrappe\.db\.get_list\b", r"\bfrappe\.db\.get_value\b", r"\bfrappe\.db\.get_values\b", r"\bfrappe\.db\.get_single_value\b", r"\bfrappe\.db\.count\b", r"\bfrappe\.db\.exists\b"],
	"write": [r"\bfrappe\.db\.set_value\b", r"\bfrappe\.db\.set_single_value\b", r"\.db_set\b", r"\bfrappe\.db\.delete\b", r"\bfrappe\.delete_doc\b", r"\bfrappe\.db\.truncate\b", r"\.insert\(", r"\.save\(", r"\.submit\(", r"\.cancel\(", r"\.delete\("],
	"sendmail": [r"\bfrappe\.sendmail\b", r"\bsendmail\b", r"\bsend_mail\b"],
	"enqueue": [r"\bfrappe\.enqueue\b", r"\benqueue_doc\b", r"\benqueue\b"],
	"file_io": [r"\bopen\(", r"\bos\.remove\b", r"\bos\.unlink\b", r"\bos\.rmdir\b", r"\bshutil\.", r"\bos\.makedirs\b", r"\bos\.path\.join\b", r"\bsend_file\b", r"\bos\.rename\b"],
	"subprocess": [r"\bsubprocess\.", r"\bos\.system\b", r"\bos\.popen\b", r"\bPopen\b", r"\bcheck_output\b"],
	"eval_exec": [r"\bsafe_exec\b", r"\bsafe_eval\b", r"\bfrappe\.safe_eval\b", r"\beval\(", r"\bexec\(", r"\bcompile\(", r"\b__import__\b", r"\bget_attr\b", r"\bfrappe\.call\b", r"\bpickle\.loads\b", r"\byaml\.load\b"],
	"render": [r"\bfrappe\.render_template\b", r"\brender_template\b", r"\bfrappe\.render\b", r"\bTemplate\(", r"\bget_jenv\b", r"\bfrappe\.utils\.jinja\b"],
	"http_out": [r"\brequests\.(get|post|put|delete|patch|request)\b", r"\bmake_get_request\b", r"\bmake_post_request\b", r"\bmake_request\b", r"\burlopen\b", r"\bhttpx\."],
	"auth": [r"\blogin_manager\b", r"\bfrappe\.local\.login_manager\b", r"\bset_user\b", r"\bupdate_password\b", r"\bfrappe\.set_user\b", r"\bgenerate_hash\b"],
	"import_module": [r"\bfrappe\.get_attr\b", r"\bget_attr\b", r"\bimportlib\b", r"\bfrappe\.get_module\b", r"\bfrappe\.scrub\b.*import"],
}
SINKS_RE = {k: [re.compile(p) for p in v] for k, v in SINKS.items()}

PERM_PATTERNS = {
	"only_for": r"\bfrappe\.only_for\b|\bonly_for\(",
	"has_permission": r"\bfrappe\.has_permission\b|\bhas_permission\(",
	"check_permission": r"\.check_permission\(|\bcheck_permission\(",
	"only_has_select_perm": r"\bonly_has_select_perm\b",
	"validate_permission": r"\bvalidate_permission|\bcheck_doctype_permission|\bcheck_admin_or_system_manager|\bcheck_role",
	"has_website_permission": r"\bhas_website_permission\b",
	"guest_check": r"frappe\.session\.user\s*==\s*[\"']Guest[\"']|frappe\.session\.user\s*!=\s*[\"']Guest[\"']|is_guest",
	"user_match_check": r"frappe\.session\.user\s*(==|!=)\s*(?![\"']Guest)",
	"role_check": r"\bfrappe\.get_roles\b|\bin\s+frappe\.get_roles|\"System Manager\"\s+in|'System Manager'\s+in",
	"rate_limit": r"@rate_limit|\brate_limit\(",
	"read_only": r"@frappe\.read_only|@read_only",
	"validate_auth": r"validate_auth|check_session|validate_csrf",
	"permission_decorator": r"@frappe\.validate_and_sanitize_search_inputs|@validate_and_sanitize_search_inputs",
}
PERM_RE = {k: re.compile(v) for k, v in PERM_PATTERNS.items()}

IGNORE_PERM_RE = re.compile(r"ignore_permissions\s*=\s*(True|1)\b|ignore_permissions=True|flags\.ignore_permissions\s*=\s*(True|1)\b")


def iter_py():
	for dirpath, dirnames, filenames in os.walk(APP):
		dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
		for f in filenames:
			if f.endswith(".py"):
				yield os.path.join(dirpath, f)


def find_files(exts, dir_names):
	"""Relative paths of files under ROOT whose directory or own stem matches `dir_names`."""
	found = []
	for dirpath, dirnames, filenames in os.walk(ROOT):
		dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
		rel_dir = os.path.relpath(dirpath, ROOT)
		in_dir = bool(set(rel_dir.split(os.sep)) & set(dir_names))
		for f in filenames:
			stem, ext = os.path.splitext(f)
			if ext in exts and (in_dir or stem in dir_names):
				found.append(os.path.relpath(os.path.join(dirpath, f), ROOT))
	return sorted(found)


def dotted(node):
	parts = []
	while isinstance(node, ast.Attribute):
		parts.append(node.attr)
		node = node.value
	if isinstance(node, ast.Name):
		parts.append(node.id)
	elif isinstance(node, ast.Call):
		parts.append("()")
	return ".".join(reversed(parts))


def dec_name(d):
	if isinstance(d, ast.Call):
		return dotted(d.func)
	return dotted(d)


def ann_str(a):
	if a is None:
		return None
	try:
		return ast.unparse(a)
	except Exception:
		return None


def literal(node):
	try:
		return ast.literal_eval(node)
	except Exception:
		try:
			return ast.unparse(node)
		except Exception:
			return None


class FuncInfo:
	__slots__ = ("qual", "file", "line", "endline", "name", "cls", "module", "decorators", "params",
	             "src", "calls", "whitelist", "is_method")


def collect(path, module):
	try:
		tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
	except SyntaxError:
		return [], {}
	src_lines = open(path, encoding="utf-8").read().split("\n")
	out = []
	imports = {}
	for n in ast.walk(tree):
		if isinstance(n, ast.ImportFrom) and n.module:
			for a in n.names:
				imports[a.asname or a.name] = f"{n.module}.{a.name}"
		elif isinstance(n, ast.Import):
			for a in n.names:
				imports[a.asname or a.name] = a.name

	def handle_func(node, cls):
		fi = FuncInfo()
		fi.name = node.name
		fi.cls = cls
		fi.module = module
		fi.qual = f"{module}.{cls + '.' if cls else ''}{node.name}"
		fi.file = path
		fi.line = node.lineno
		fi.endline = getattr(node, "end_lineno", node.lineno)
		fi.is_method = bool(cls)
		fi.decorators = [dec_name(d) for d in node.decorator_list]
		fi.src = "\n".join(src_lines[node.lineno - 1: fi.endline])
		params = []
		a = node.args
		allargs = list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)
		defaults = {}
		nd = len(a.defaults)
		pos = list(a.posonlyargs) + list(a.args)
		for i, d in enumerate(a.defaults):
			defaults[pos[len(pos) - nd + i].arg] = literal(d)
		for kw, d in zip(a.kwonlyargs, a.kw_defaults, strict=False):
			if d is not None:
				defaults[kw.arg] = literal(d)
		for arg in allargs:
			if arg.arg in ("self", "cls"):
				continue
			params.append({"name": arg.arg, "type": ann_str(arg.annotation),
			               "default": defaults.get(arg.arg) if arg.arg in defaults else None,
			               "required": arg.arg not in defaults})
		if a.vararg:
			params.append({"name": "*" + a.vararg.arg, "type": ann_str(a.vararg.annotation), "default": None, "required": False})
		if a.kwarg:
			params.append({"name": "**" + a.kwarg.arg, "type": ann_str(a.kwarg.annotation), "default": None, "required": False})
		fi.params = params
		# whitelist decorator
		fi.whitelist = None
		for d in node.decorator_list:
			nm = dec_name(d)
			if nm in ("frappe.whitelist", "whitelist"):
				info = {"allow_guest": False, "xss_safe": False, "methods": None, "force_types": None}
				if isinstance(d, ast.Call):
					for kwn in d.keywords:
						if kwn.arg in info:
							info[kwn.arg] = literal(kwn.value)
				fi.whitelist = info
		# calls
		calls = set()
		for sub in ast.walk(node):
			if isinstance(sub, ast.Call):
				nm = dotted(sub.func)
				if nm:
					calls.add(nm)
		fi.calls = calls
		out.append(fi)

	def walk_body(body, cls):
		for node in body:
			if isinstance(node, ast.ClassDef):
				walk_body(node.body, node.name)
			elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
				handle_func(node, cls)
				for sub in node.body:
					if isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef):
						pass
	walk_body(tree.body, None)
	return out, imports


def module_name(path):
	rel = os.path.relpath(path, ROOT)
	return rel[:-3].replace("/", ".").replace(".__init__", "")


def scan_text(text, regexes):
	hits = []
	for k, pats in regexes.items():
		for p in pats:
			if p.search(text):
				hits.append(k)
				break
	return hits


def git_commit():
	try:
		return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
		                      capture_output=True, text=True, check=True).stdout.strip()
	except (subprocess.CalledProcessError, OSError):
		return None


def detect_app_package(root):
	"""The package directory holding hooks.py — that is what makes a checkout a Frappe app."""
	candidates = []
	for name in sorted(os.listdir(root)):
		path = os.path.join(root, name)
		if name in SKIP_DIRS or not os.path.isdir(path):
			continue
		if os.path.exists(os.path.join(path, "hooks.py")):
			candidates.append(name)
	if len(candidates) == 1:
		return candidates[0]
	if not candidates:
		sys.exit(f"No package with hooks.py found under {root}. Pass --module explicitly.")
	sys.exit(f"Several packages with hooks.py found under {root}: {', '.join(candidates)}. "
	         "Pass --module to choose one.")


def main():
	funcs = []
	by_qual = {}
	by_simple = defaultdict(list)
	by_module = defaultdict(dict)
	imports_by_module = {}
	files = list(iter_py())
	for path in files:
		mod = module_name(path)
		fs, imports = collect(path, mod)
		imports_by_module[mod] = imports
		for f in fs:
			funcs.append(f)
			by_qual[f.qual] = f
			by_simple[f.name].append(f)
			by_module[mod][f.cls + "." + f.name if f.cls else f.name] = f

	# direct sinks / perms per function
	direct = {}
	for f in funcs:
		direct[f.qual] = {
			"sinks": set(scan_text(f.src, SINKS_RE)),
			"perms": {k for k, r in PERM_RE.items() if r.search(f.src)},
			"ignore_permissions": bool(IGNORE_PERM_RE.search(f.src)),
		}

	GENERIC = {"get", "run", "validate", "execute", "save", "insert", "delete", "update", "load",
	           "clean", "process", "send", "check", "main", "setup", "reset", "start", "stop"}

	def resolve(callname, caller):
		"""Map a call expression to callee FuncInfo objects, using imports for precision."""
		parts = callname.split(".")
		last = parts[-1]
		if not last or last == "()":
			return []
		mod_funcs = by_module.get(caller.module, {})
		imports = imports_by_module.get(caller.module, {})

		# self.method / instance method inside the same class
		if parts[0] in ("self", "cls") and len(parts) == 2 and caller.cls:
			f = mod_funcs.get(f"{caller.cls}.{last}")
			return [f] if f else []

		# bare name defined in the same module
		if len(parts) == 1:
			if last in mod_funcs:
				return [mod_funcs[last]]
			target = imports.get(last)
			if target and target in by_qual:
				return [by_qual[target]]
			if target:  # from x import y -> y may be a class; try Class.__init__ style misses
				return []
			return []

		# dotted: alias.func where alias is an imported module or class
		head = parts[0]
		target = imports.get(head)
		if target:
			cand = target + "." + ".".join(parts[1:])
			if cand in by_qual:
				return [by_qual[cand]]
			cand2 = ".".join([target, parts[-1]])
			if cand2 in by_qual:
				return [by_qual[cand2]]
		if callname in by_qual:
			return [by_qual[callname]]

		# unresolved dotted call (e.g. doc.method) -> fall back to unique name match
		if last in GENERIC:
			return []
		cands = by_simple.get(last, [])
		if len(cands) == 1:
			return cands
		if len(parts) >= 2 and parts[-2] and parts[-2][0].isupper():
			same = [c for c in cands if c.cls == parts[-2]]
			if len(same) == 1:
				return same
		return []

	MAXDEPTH = 4

	def transitive(entry):
		seen = {entry.qual}
		sinks = set(direct[entry.qual]["sinks"])
		perms = set(direct[entry.qual]["perms"])
		ignore_perm = direct[entry.qual]["ignore_permissions"]
		frontier = [(entry, 0)]
		reached = []
		while frontier:
			fn, d = frontier.pop()
			if d >= MAXDEPTH:
				continue
			for c in fn.calls:
				for cand in resolve(c, fn):
					if cand.qual in seen:
						continue
					seen.add(cand.qual)
					reached.append(cand.qual)
					dd = direct[cand.qual]
					sinks |= dd["sinks"]
					if d == 0:
						perms |= dd["perms"]
					ignore_perm = ignore_perm or dd["ignore_permissions"]
					frontier.append((cand, d + 1))
		return sinks, perms, ignore_perm, reached

	entries = []

	DOCTYPE_CALLS = re.compile(
		r"\b(?:get_doc|get_cached_doc|new_doc|get_all|get_list|get_single|get_cached_value|get_last_doc|delete_doc|get_meta|get_hooks_doc)\s*\(\s*[\"']([A-Z][A-Za-z0-9 ]{2,})[\"']"
		r"|\bdb\.(?:get_value|get_values|set_value|get_list|get_all|exists|count|delete|get_single_value)\s*\(\s*[\"']([A-Z][A-Za-z0-9 ]{2,})[\"']"
		r"|\bdoctype\s*=\s*[\"']([A-Z][A-Za-z0-9 ]{2,})[\"']"
	)

	def doctypes_in(text):
		out = set()
		for m in DOCTYPE_CALLS.finditer(text):
			out.add(next(g for g in m.groups() if g))
		return out

	def make_entry(f, kind, extra=None):
		sinks, perms, ignore_perm, reached = transitive(f)
		d = direct[f.qual]
		e = {
			"id": f.qual,
			"kind": kind,
			"module": f.module,
			"file": os.path.relpath(f.file, ROOT),
			"line": f.line,
			"name": f.name,
			"class": f.cls,
			"decorators": f.decorators,
			"allow_guest": bool(f.whitelist and f.whitelist.get("allow_guest")),
			"xss_safe": bool(f.whitelist and f.whitelist.get("xss_safe")),
			"methods": (f.whitelist.get("methods") if f.whitelist else None) or ["GET", "POST", "PUT", "DELETE"],
			"force_types": (f.whitelist.get("force_types") if f.whitelist else None),
			"params": f.params,
			"permission_checks_direct": sorted(d["perms"]),
			"permission_checks_transitive": sorted(perms),
			"has_permission_check": bool(d["perms"] & {"only_for", "has_permission", "check_permission",
			                                            "only_has_select_perm", "validate_permission",
			                                            "has_website_permission", "role_check", "guest_check"})
			or bool(perms & {"only_for", "has_permission", "check_permission", "only_has_select_perm",
			                 "validate_permission", "has_website_permission"}),
			"uses_ignore_permissions_direct": d["ignore_permissions"],
			"uses_ignore_permissions_reachable": ignore_perm,
			"sinks_direct": sorted(d["sinks"]),
			"sinks_reachable": sorted(sinks),
			"doctypes_direct": sorted(doctypes_in(f.src)),
			"doctypes_reachable": sorted(doctypes_in(f.src) | {dt for q in reached for dt in doctypes_in(by_qual[q].src)})[:60],
			"callee_sample": sorted(reached)[:25],
			"is_test": "/tests/" in f.file or os.path.basename(f.file).startswith("test_"),
			"reads_form_dict": bool(re.search(r"form_dict|frappe\.local\.request|request\.(json|data|files|args|headers)|frappe\.request", f.src)),
			"callee_count": len(reached),
		}
		if extra:
			e.update(extra)
		return e

	for f in funcs:
		if f.whitelist is not None:
			kind = "whitelisted_doctype_method" if f.is_method else "whitelisted_function"
			entries.append(make_entry(f, kind))

	# www / portal pages
	for f in funcs:
		if f.name in ("get_context", "get_list_context") and "/www/" in f.file or (
			f.name == "get_context" and "/templates/pages/" in f.file
		):
			if f.whitelist is not None:
				continue
			rel = os.path.relpath(f.file, ROOT)
			route = None
			if "/www/" in rel:
				route = "/" + rel.split("/www/")[1][:-3]
			entries.append(make_entry(f, "web_page", {"route": route, "allow_guest": True,
			                                          "methods": ["GET", "POST"]}))

	# hooks
	hook_vals = {}
	hooks_path = os.path.join(APP, "hooks.py")
	if os.path.exists(hooks_path):
		hooks_tree = ast.parse(open(hooks_path, encoding="utf-8").read())
		for n in hooks_tree.body:
			if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
				hook_vals[n.targets[0].id] = literal(n.value)

	def hook_entry(dotted_path, kind, meta):
		fn = by_qual.get(dotted_path)
		if fn:
			e = make_entry(fn, kind, meta)
			e["allow_guest"] = meta.get("allow_guest", False)
			return e
		return {"id": dotted_path, "kind": kind, "resolved": False, **meta}

	hook_entries = []
	for evt, jobs in (hook_vals.get("scheduler_events") or {}).items():
		if isinstance(jobs, dict):
			for cron, jl in jobs.items():
				for j in jl:
					hook_entries.append(hook_entry(j, "scheduled_job", {"schedule": f"{evt}:{cron}"}))
		else:
			for j in jobs or []:
				hook_entries.append(hook_entry(j, "scheduled_job", {"schedule": evt}))

	for hookname in ("on_session_creation", "on_login", "on_logout", "before_request", "after_request",
	                 "before_job", "after_job", "notification_config", "auth_hooks", "before_migrate",
	                 "after_migrate", "website_context", "update_website_context", "extend_bootinfo",
	                 "get_website_user_home_page", "standard_queries", "sounds", "jenv"):
		v = hook_vals.get(hookname)
		if not v:
			continue
		vals = v if isinstance(v, list) else [v]
		for item in vals:
			if isinstance(item, str):
				hook_entries.append(hook_entry(item, "hook_callback", {"hook": hookname,
					"allow_guest": hookname in ("before_request", "after_request", "website_context",
					                            "update_website_context", "auth_hooks", "jenv")}))

	for hookname in ("has_permission", "permission_query_conditions", "has_website_permission",
	                 "override_whitelisted_methods", "doc_events", "override_doctype_class",
	                 "website_route_rules"):
		v = hook_vals.get(hookname)
		if isinstance(v, dict):
			for k, item in v.items():
				if isinstance(item, str):
					hook_entries.append(hook_entry(item, "hook_callback", {"hook": hookname, "target": k}))
				elif isinstance(item, dict):
					for evt, m in item.items():
						ms = m if isinstance(m, list) else [m]
						for mm in ms:
							if isinstance(mm, str):
								hook_entries.append(hook_entry(mm, "hook_callback",
									{"hook": hookname, "target": f"{k}:{evt}"}))
	entries.extend(hook_entries)

	# route rules
	routes = []
	for r in hook_vals.get("website_route_rules") or []:
		routes.append({"kind": "website_route_rule", **r})
	for r in hook_vals.get("website_redirects") or []:
		routes.append({"kind": "website_redirect", **r})

	# every file under www/ and templates/pages/ is a guest-reachable route
	for base in (os.path.join(APP, "www"), os.path.join(APP, "templates", "pages")):
		for dirpath, dirnames, filenames in os.walk(base):
			dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
			for fn in filenames:
				if fn.startswith("__") or not fn.endswith((".py", ".html", ".md")):
					continue
				p = os.path.join(dirpath, fn)
				rel = os.path.relpath(p, ROOT)
				stem = os.path.splitext(rel.split("/www/")[-1] if "/www/" in rel else rel.split("/pages/")[-1])[0]
				r = {"kind": "portal_page", "route": "/" + stem, "file": rel}
				if fn.endswith(".py"):
					text = open(p, encoding="utf-8", errors="ignore").read()
					r["no_cache"] = "no_cache" in text
					r["sitemap"] = "sitemap" in text
					r["base_template_path"] = "base_template_path" in text
					r["has_get_context"] = "def get_context" in text
					r["guest_redirect_or_login_check"] = bool(re.search(
						r"Guest|login_required|frappe\.throw\(.*Permission|redirect_to_login", text))
					r["sinks"] = scan_text(text, SINKS_RE)
				routes.append(r)

	# socketio handlers
	socket_handlers = []
	for js in find_files((".js", ".ts"), ("realtime", "socketio")):
		p = os.path.join(ROOT, js)
		text = open(p, encoding="utf-8", errors="ignore").read()
		for m in re.finditer(r"socket\.on\(\s*[\"'`]([^\"'`]+)[\"'`]\s*,\s*(?:async\s*)?(?:function\s*)?\(([^)]*)\)", text):
			socket_handlers.append({"kind": "socketio_handler", "event": m.group(1),
			                        "params": [a.strip() for a in m.group(2).split(",") if a.strip()],
			                        "file": js, "line": text[:m.start()].count("\n") + 1})
	# socketio auth middlewares
	mw = []
	for dirpath, dirnames, filenames in os.walk(ROOT):
		dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
		if os.path.basename(dirpath) == "middlewares" and "realtime" in dirpath.split(os.sep):
			mw.extend(sorted(os.path.relpath(os.path.join(dirpath, f), ROOT) for f in filenames))

	# api route surface
	api_routes = []
	for fname in find_files((".py",), ("api",)):
		p = os.path.join(ROOT, fname)
		text = open(p, encoding="utf-8", errors="ignore").read()
		if "Rule(" not in text:
			continue
		for m in re.finditer(r"Rule\(\s*[\"']([^\"']+)[\"']\s*,([^)]*)\)", text):
			api_routes.append({"kind": "api_route", "rule": m.group(1),
			                   "spec": " ".join(m.group(2).split()), "file": fname,
			                   "line": text[:m.start()].count("\n") + 1})

	# ---- reference counting: find call sites outside the defining file ----
	ref_exts = (".py", ".js", ".ts", ".vue", ".html", ".json", ".md")
	corpus = []
	for dirpath, dirnames, filenames in os.walk(ROOT):
		dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
		for fn in filenames:
			if fn.endswith(ref_exts):
				p = os.path.join(dirpath, fn)
				try:
					corpus.append((os.path.relpath(p, ROOT), open(p, encoding="utf-8", errors="ignore").read()))
				except OSError:
					pass

	path_needles = {}
	name_needles = {}
	for e in entries:
		if not e.get("kind", "").startswith("whitelisted"):
			continue
		if not e.get("class"):
			path_needles[e["id"]] = f"{e['module']}.{e['name']}"
		name_needles[e["id"]] = [f'"{e["name"]}"', f"'{e['name']}'", f"`{e['name']}`"]

	path_files = defaultdict(set)
	name_files = defaultdict(set)
	for rel, text in corpus:
		for eid, pat in path_needles.items():
			if pat in text:
				path_files[eid].add(rel)
		for eid, pats in name_needles.items():
			if any(p in text for p in pats):
				name_files[eid].add(rel)

	for e in entries:
		if e["id"] not in name_needles:
			continue
		own = e["file"]
		prefs = path_files[e["id"]] - {own}
		nrefs = name_files[e["id"]] - {own}
		e["external_reference_files"] = sorted(prefs or nrefs)[:8]
		e["external_reference_count"] = len(prefs)
		e["name_reference_count"] = len(nrefs)
		e["unreferenced"] = not prefs and not nrefs

	summary = {
		"repo": ROOT,
		"app": os.path.basename(APP),
		"commit": git_commit(),
		"total_entry_points": len(entries),
		"by_kind": dict(sorted(((k, sum(1 for e in entries if e.get("kind") == k)) for k in {e.get("kind") for e in entries}))),
		"guest_allowed": sum(1 for e in entries if e.get("allow_guest")),
		"no_permission_check": sum(1 for e in entries if not e.get("has_permission_check") and not e.get("is_test")),
		"whitelisted_total": sum(1 for e in entries if e.get("kind", "").startswith("whitelisted")),
		"whitelisted_guest": sum(1 for e in entries if e.get("kind", "").startswith("whitelisted") and e.get("allow_guest")),
		"no_declared_methods": sum(1 for e in entries if e.get("kind", "").startswith("whitelisted") and e.get("methods") == ["GET", "POST", "PUT", "DELETE"]),
		"tests_included": sum(1 for e in entries if e.get("is_test")),
		"unreferenced_whitelisted": sum(1 for e in entries if e.get("unreferenced")),
		"guest_no_permission_check": sum(1 for e in entries if e.get("allow_guest") and not e.get("has_permission_check")),
	}

	def ids(pred):
		return sorted(e["id"] for e in entries if not e.get("is_test") and pred(e))

	views = {
		"guest_no_permission_check": ids(lambda e: e.get("allow_guest") and not e.get("has_permission_check")),
		"guest_reaching_sql": ids(lambda e: e.get("allow_guest") and "sql" in (e.get("sinks_reachable") or [])),
		"guest_reaching_write": ids(lambda e: e.get("allow_guest") and "write" in (e.get("sinks_reachable") or [])),
		"reaching_eval_exec": ids(lambda e: "eval_exec" in (e.get("sinks_direct") or [])),
		"reaching_subprocess": ids(lambda e: "subprocess" in (e.get("sinks_reachable") or [])),
		"reaching_render_template": ids(lambda e: "render" in (e.get("sinks_direct") or [])),
		"reaching_http_out": ids(lambda e: "http_out" in (e.get("sinks_direct") or [])),
		"sql_direct": ids(lambda e: "sql" in (e.get("sinks_direct") or [])),
		"ignore_permissions_direct": ids(lambda e: e.get("uses_ignore_permissions_direct") and e.get("kind", "").startswith("whitelisted")),
		"no_declared_methods": ids(lambda e: e.get("kind", "").startswith("whitelisted") and e.get("methods") == ["GET", "POST", "PUT", "DELETE"]),
		"unreferenced_candidates_for_removal": ids(lambda e: e.get("unreferenced")),
		"untyped_params": ids(lambda e: e.get("kind", "").startswith("whitelisted") and any(p.get("type") is None for p in e.get("params", []))),
		"reads_form_dict": ids(lambda e: e.get("reads_form_dict") and e.get("kind", "").startswith("whitelisted")),
	}

	out = {
		"schema": "frappe-endpoint-inventory/1",
		"summary": summary,
		"views": views,
		"entry_points": entries,
		"website_routes": routes,
		"socketio_handlers": socket_handlers,
		"socketio_middlewares": mw,
		"api_routes": api_routes,
		"notes": {
			"call_graph_depth": MAXDEPTH,
			"resolution": "callee resolved by simple name across the app; ambiguous names (>6 defs) dropped",
			"sinks_reachable": "union of direct sinks over the transitive callee set",
			"has_permission_check": "regex presence of an explicit permission gate in the entry function or (weaker) its direct callees; presence is not proof of correctness",
		},
	}
	with open(DEST, "w", encoding="utf-8") as fh:
		json.dump(out, fh, indent=1)
	print(json.dumps(summary, indent=1))


def parse_args():
	global ROOT, APP, DEST, SKIP_DIRS
	p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	p.add_argument("output", help="path to write the inventory JSON to")
	p.add_argument("--root", default=os.getcwd(), help="app repository checkout (default: current directory)")
	p.add_argument("--module", help="package inside the checkout holding hooks.py (default: detected)")
	p.add_argument("--skip-dir", action="append", default=[], metavar="NAME",
	               help="extra directory name to skip, repeatable")
	a = p.parse_args()
	SKIP_DIRS = DEFAULT_SKIP_DIRS | set(a.skip_dir)
	ROOT = os.path.abspath(a.root)
	if not os.path.isdir(ROOT):
		sys.exit(f"Not a directory: {ROOT}")
	APP = os.path.join(ROOT, a.module or detect_app_package(ROOT))
	if not os.path.isdir(APP):
		sys.exit(f"Not a directory: {APP}")
	DEST = os.path.abspath(a.output)


parse_args()
main()
