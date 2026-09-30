"""Static endpoint inventory builder for a Frappe app checkout (read-only).

Usage:
    python build_inventory.py OUTPUT.json [--root APP_CHECKOUT] [--module MODULE_NAME]

`--root` is the app repository checkout (default: current directory). `--module` is the
Python package inside it that holds `hooks.py`; it is detected automatically when omitted.

Beyond enumerating entry points, this builder encodes what the framework already checks, so a
scanner is not left to rediscover it per candidate. Three products carry that:

  * `doctypes`     — every DocType JSON's permission rows, resolved at permlevel 0 per right,
                     with `admin_only` and `public_read` derived. See `_framework-guards.md` §6.
  * `guard.class`  — how each entry point is guarded, including `doc_layer_only` (the framework
                     checks it: `_framework-guards.md` §1) and `run_doc_method_read_gate` (§2a).
  * `refuted_by_framework` — entry points a pattern search flags and the framework guards, each
                     with the reason. These are non-findings. Read the reason before overriding.

Everything here is static and therefore a prior, not a verdict: a live site can carry
`Custom DocPerm` rows, `ignore_permissions` can be set by a caller several frames up, and the
call-graph resolution is name-based. Read the real code before reporting anything.
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
EXTRA_DOCTYPE_ROOTS = []  # other app checkouts whose DocType permission rows to load
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

# The categories above are coarse: `get_list` mixes the permissioned read with the unpermissioned
# one, and `write` mixes the write the document layer checks with the write that bypasses it. Both
# conflations produce false positives, so these finer categories exist alongside them. Sourced from
# `_framework-guards.md` §1 and §3.
REFINED_SINKS = {
	# reads that apply no permission of their own
	"read_unpermissioned": [
		r"\bfrappe\.get_all\b", r"\bfrappe\.db\.get_all\b", r"\bfrappe\.db\.get_list\b",
		r"\bfrappe\.db\.get_value\b", r"\bfrappe\.db\.get_values\b", r"\bfrappe\.db\.get_single_value\b",
		r"\bfrappe\.db\.count\b", r"\bfrappe\.db\.exists\b", r"\bfrappe\.db\.sql\b",
		r"\bfrappe\.db\.multisql\b", r"\bfrappe\.qb\.from_\b", r"\bfrappe\.get_cached_value\b",
	],
	# reads that do apply permissions
	"read_permissioned": [r"\bfrappe\.get_list\b", r"\bfrappe\.client\.get_list\b", r"\bfrappe\.desk\.reportview\b"],
	# the query builder's permission switch defaults to ignore_permissions=True. A query assembled
	# from `frappe.qb.DocType(...)` and executed with `.run()` never goes near get_query at all, so
	# it carries no permission of any kind — match that shape too.
	"query_builder": [r"\bfrappe\.qb\.get_query\b", r"\bget_query\(", r"\bfrappe\.qb\.DocType\b",
	                  r"\bqb\.DocType\(", r"\bqb\.Table\(",
	                  r"\.run\(\s*\)", r"\.run\(\s*(as_dict|as_list|pluck|debug)\b"],
	# writes the document layer checks for you: save/insert/submit/cancel/delete and the mapper
	# Document methods take no positional arguments, so this skips `list.insert(0, x)` and the like
	"write_doc_layer": [r"\.(?:insert|save|submit|cancel|delete)\(\s*(?:\)|\w+\s*=)",
	                    r"\bfrappe\.delete_doc\b", r"\bget_mapped_doc\b"],
	# writes that bypass the document layer entirely — the genuinely unguarded ones
	"write_db_bypass": [r"\bfrappe\.db\.set_value\b", r"\bfrappe\.db\.set_single_value\b",
	                    r"\.db_set\b", r"\.db_update\b", r"\bfrappe\.db\.delete\b",
	                    r"\bfrappe\.db\.truncate\b", r"\bfrappe\.db\.rename_doc\b",
	                    r"\bfrappe\.db\.bulk_insert\b", r"\bupdate_password\b"],
	# a document loaded by name, the input side of most authorization findings
	"doc_load": [r"\bfrappe\.get_doc\b", r"\bfrappe\.get_cached_doc\b", r"\bfrappe\.get_lazy_doc\b",
	             r"\bfrappe\.get_last_doc\b", r"\bfrappe\.new_doc\b"],
}
SINKS.update(REFINED_SINKS)
SINKS_RE = {k: [re.compile(p) for p in v] for k, v in SINKS.items()}

# `frappe.qb.get_query(..., ignore_permissions=False)` is the permissioned form, and it authorizes
# on `select`, not `read`.
GET_QUERY_PERMISSIONED_RE = re.compile(r"ignore_permissions\s*=\s*False")
# `@frappe.whitelist()` enforces scalar annotations through pydantic; a container annotation
# guarantees only the container, and an unannotated parameter is not validated at all (§4).
CONTAINER_TYPES = re.compile(r"^\s*(dict|list|tuple|set|Any|object|DynamicDict|_dict|frappe\._dict)\b|\bdict\b|\blist\b")
# sinks that turn a caller-supplied name into an authorization decision — the operator-injection
# shape of §4a
NAME_TO_AUTH_SINK = re.compile(
	r"\b(?:frappe\.get_doc|frappe\.get_cached_doc|frappe\.get_lazy_doc|frappe\.db\.get_value"
	r"|frappe\.db\.exists|frappe\.db\.get_values|has_permission|check_permission)\s*\("
)

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

# frappe/permissions.py: AUTOMATIC_ROLES. Nobody grants these — `get_roles()` returns them for
# every user of the matching type, so a right held by one of them is held by everyone, and a role
# gap naming one is not a gap. See `_framework-guards.md` §6.
AUTOMATIC_ROLES = {"Guest", "All", "Desk User", "Administrator"}
# "All" and "Guest" reach Website Users too; "Desk User" reaches only System Users, so a grant to it
# is public to desk users and not to a whitelisted call from a portal user.
PUBLIC_ROLES = {"All", "Guest"}
# frappe/permissions.py: std_rights
RIGHTS = ("select", "read", "write", "create", "delete", "submit", "cancel", "amend",
          "report", "export", "import", "share", "print", "email")


def load_doctypes(root, source):
	"""Every DocType defined under `root`, with its permission rows resolved per right.

	The permission model is the difference between a role gap and a non-finding, and three of its
	rules are easy to get wrong in a scanner (`_framework-guards.md` §6): permlevel > 0 governs
	fields and never document access; the automatic roles cannot be a gap; and a child table carries
	no permission rows at all. All three are resolved here so no prompt has to.

	Call it once per checkout that matters. An app's endpoints routinely read doctypes the framework
	or another installed app defines, and a doctype this builder has never seen cannot refute
	anything — so pass `--doctypes-from <other app checkout>` for each of them.
	"""
	doctypes = {}
	by_dir = {}
	for dirpath, dirnames, filenames in os.walk(root):
		dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
		if os.path.basename(os.path.dirname(dirpath)) != "doctype":
			continue
		for fn in filenames:
			if not fn.endswith(".json"):
				continue
			path = os.path.join(dirpath, fn)
			try:
				with open(path, encoding="utf-8") as fh:
					d = json.load(fh)
			except (OSError, ValueError):
				continue
			if not isinstance(d, dict) or d.get("doctype") != "DocType" or not d.get("name"):
				continue
			istable = bool(int(d.get("istable") or 0))
			perms = d.get("permissions") or []
			# permlevel 0 is the only level that decides whether a document can be opened
			level0 = [p for p in perms if not int(p.get("permlevel") or 0)]
			roles_by_right = {}
			for right in RIGHTS:
				roles_by_right[right] = sorted({p.get("role") for p in level0
				                                if p.get("role") and int(p.get(right) or 0)})
			read_roles = set(roles_by_right["read"])
			select_roles = set(roles_by_right["select"]) | read_roles  # read implies select in practice
			entry = {
				"name": d["name"],
				"module": d.get("module"),
				"source": source,
				"file": os.path.relpath(path, root),
				"istable": istable,
				"issingle": bool(int(d.get("issingle") or 0)),
				"read_only": bool(int(d.get("read_only") or 0)),
				"is_submittable": bool(int(d.get("is_submittable") or 0)),
				"is_tree": bool(int(d.get("is_tree") or 0)),
				"has_web_view": bool(int(d.get("has_web_view") or 0)),
				"permission_rows_total": len(perms),
				"permission_rows_permlevel0": len(level0),
				"roles_by_right_permlevel0": {k: v for k, v in roles_by_right.items() if v},
				"if_owner_roles": sorted({p.get("role") for p in level0 if int(p.get("if_owner") or 0)}),
				# nobody but Administrator holds read at permlevel 0 -> unreachable through
				# run_doc_method, and not reachable by any role at all. A child table is not this:
				# it carries no rows because the parent authorizes it, so exclude it explicitly.
				"admin_only": not istable and bool(perms) and not (read_roles - {"Administrator"}),
				# every logged-in user, Website Users included, is entitled to this by design
				"public_read": bool(read_roles & PUBLIC_ROLES),
				"desk_read": "Desk User" in read_roles,
				"guest_read": "Guest" in read_roles,
				"public_select": bool(select_roles & PUBLIC_ROLES),
				"no_permission_rows": not perms,
			}
			doctypes[d["name"]] = entry
			by_dir[os.path.basename(dirpath)] = d["name"]
	return doctypes, by_dir


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
	             "src", "calls", "whitelist", "is_method", "string_annotations")


def collect(path, module):
	try:
		tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
	except SyntaxError:
		return [], {}
	src_lines = open(path, encoding="utf-8").read().split("\n")
	# transform_parameter_types skips str annotations, so this import turns off the whitelist's
	# type validation for every function in the module
	string_annotations = any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
	                         and any(a.name == "annotations" for a in n.names) for n in tree.body)
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
		fi.string_annotations = string_annotations
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


def required_apps(app_dir):
	"""`required_apps` from an app package's hooks.py; `org/repo` entries reduce to `repo`."""
	try:
		with open(os.path.join(app_dir, "hooks.py"), encoding="utf-8") as fh:
			tree = ast.parse(fh.read())
	except (OSError, SyntaxError):
		return []
	for node in tree.body:
		if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "required_apps" for t in node.targets)
		    and isinstance(node.value, (ast.List, ast.Tuple))):
			return [e.value.rstrip("/").split("/")[-1] for e in node.value.elts
			        if isinstance(e, ast.Constant) and isinstance(e.value, str)]
	return []


def discover_dependency_checkouts(root, app_dir):
	"""frappe and the transitive `required_apps`, found as siblings in `<bench>/apps`."""
	apps_dir = os.path.dirname(root)
	found, queue, seen = [], ["frappe"] + required_apps(app_dir), set()
	while queue:
		name = queue.pop(0)
		if name in seen:
			continue
		seen.add(name)
		checkout = os.path.join(apps_dir, name)
		if not os.path.isdir(checkout) or os.path.samefile(checkout, root):
			continue
		found.append(checkout)
		pkg = os.path.join(checkout, name)
		queue.extend(required_apps(pkg if os.path.isdir(pkg) else checkout))
	return found


def main():
	# the app's own doctypes, then every other checkout we were pointed at. The app's own
	# definitions win a name collision: it is the one being audited.
	doctypes, doctype_by_dir = {}, {}
	for extra_root in reversed(EXTRA_DOCTYPE_ROOTS):
		dts, by_dir = load_doctypes(extra_root, os.path.basename(extra_root.rstrip(os.sep)))
		doctypes.update(dts)
		doctype_by_dir.update(by_dir)
	own, own_by_dir = load_doctypes(ROOT, os.path.basename(ROOT.rstrip(os.sep)))
	doctypes.update(own)
	doctype_by_dir.update(own_by_dir)
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

	EXPLICIT_CHECKS = {"only_for", "has_permission", "check_permission", "only_has_select_perm",
	                   "validate_permission", "has_website_permission"}
	DATA_SINKS = {"read_unpermissioned", "read_permissioned", "write_doc_layer",
	              "write_db_bypass", "doc_load", "sql", "query_builder"}

	def owning_doctype(f):
		"""The DocType whose controller this file is, if it is one.

		A `<doctype>/<scrub>/<scrub>.py` module is that DocType's controller, so a whitelisted
		method on it is reachable only through `run_doc_method` — which read-gates the parent
		(`_framework-guards.md` §2a). The JSON beside it is authoritative for the name; the
		directory name is scrubbed and cannot be unscrubbed reliably.
		"""
		parts = os.path.relpath(f.file, ROOT).split(os.sep)
		if len(parts) >= 3 and parts[-3] == "doctype":
			return doctype_by_dir.get(parts[-2])
		return None

	def classify_guard(f, d, sinks, perms, ignore_perm, kind, dt_owner):
		"""How this entry point is guarded — and, where the framework guards it, say so.

		The classes that matter for the false positive rate are `doc_layer_only` (§1) and
		`run_doc_method_read_gate` (§2a): both look unguarded at the wrapper and are not. The
		classes that matter for the true positive rate are `db_bypass_unguarded` and
		`unpermissioned_read`.
		"""
		direct_sinks = d["sinks"]
		explicit = sorted(d["perms"] & EXPLICIT_CHECKS)
		explicit_deep = sorted((perms - d["perms"]) & EXPLICIT_CHECKS)
		doc_layer = "write_doc_layer" in direct_sinks
		bypass = "write_db_bypass" in direct_sinks
		unperm_read = "read_unpermissioned" in direct_sinks
		qb = "query_builder" in direct_sinks
		g = {
			"explicit_checks_in_body": explicit,
			"explicit_checks_in_callees": explicit_deep,
			"writes_through_document_layer": doc_layer,
			"writes_bypassing_document_layer": bypass,
			"reads_without_permission": unperm_read,
			"reads_with_permission": "read_permissioned" in direct_sinks,
			"uses_query_builder": qb,
			# get_query defaults to ignore_permissions=True; when the call passes False it
			# authorizes on `select`, not `read` (§3)
			"query_builder_permissioned": bool(qb and GET_QUERY_PERMISSIONED_RE.search(f.src)),
			"ignore_permissions": ignore_perm,
			"search_input_decorator": "permission_decorator" in d["perms"],
		}
		if explicit:
			g["class"] = "explicit_check"
			g["note"] = "an explicit permission call is in the body — read whether it covers this actor and this object"
		elif kind == "whitelisted_doctype_method":
			g["class"] = "run_doc_method_read_gate"
			g["note"] = ("reachable only through run_doc_method, which loads the document with "
			             "check_permission=True: gated on read, NOT on write (§2a). The v2 route checks write for POST")
			if dt_owner and doctypes.get(dt_owner, {}).get("admin_only"):
				g["class"] = "unreachable_admin_only_doctype"
				g["note"] = (f"{dt_owner} grants read at permlevel 0 to no role but Administrator, so "
				             "run_doc_method refuses the document load before this body runs — not a finding")
		elif ignore_perm:
			g["class"] = "ignore_permissions"
			g["note"] = "ignore_permissions is set on the path — trace which call it applies to"
		elif bypass:
			g["class"] = "db_bypass_unguarded"
			g["note"] = "writes bypass the document layer with no explicit check in the body — a candidate"
		# an unpermissioned read beside a document-layer write is the §1a shape, so it wins
		elif unperm_read:
			g["class"] = "unpermissioned_read"
			g["note"] = "reads through a call that applies no permission — a candidate if the data is not the caller's"
		elif doc_layer:
			g["class"] = "doc_layer_only"
			g["note"] = ("every write goes through save/insert/submit/cancel/delete or get_mapped_doc, "
			             "which check permissions themselves (§1) — NOT a finding on its own. It is one "
			             "only if a document it reads is not the document it writes (§1a)")
		elif explicit_deep:
			g["class"] = "check_in_callee"
			g["note"] = "the only permission call is in a callee — confirm it covers this actor and object"
		elif not (direct_sinks & DATA_SINKS):
			# A thin wrapper that delegates to a helper has no sink of its own, and calling that
			# "nothing to authorize" is how a real finding gets dropped: the sink is one frame down.
			# Separate the two cases rather than collapsing them.
			if sinks & DATA_SINKS:
				g["class"] = "delegates"
				g["note"] = ("no sink in the body, but its callees reach "
				             + ", ".join(sorted(sinks & DATA_SINKS))
				             + " — read the callee, and read what this wrapper passes it")
			else:
				g["class"] = "compute_only"
				g["note"] = "no read or write sink in the body or its callees — nothing to authorize"
		else:
			g["class"] = "unclassified"
			g["note"] = "read it"
		return g

	def container_params(f):
		"""Parameters through which an operator payload can still arrive (§4).

		A scalar annotation is enforced by pydantic, so `name: str` rejects a list with 417. A
		`dict`/`list` annotation guarantees only the container, and an unannotated parameter is not
		validated at all. A string annotation is skipped, and a default of another type widens the
		accepted type.
		"""
		out = []
		for p in f.params:
			nm = p["name"].lstrip("*")
			t = p.get("type")
			unvalidated = t is None or f.string_annotations or t[:1] in ("'", '"')
			if unvalidated or CONTAINER_TYPES.search(t) or isinstance(p.get("default"), (dict, list)):
				out.append({"name": nm, "type": t, "validated": not unvalidated,
				            "reaches_auth_sink": bool(re.search(
					            NAME_TO_AUTH_SINK.pattern + r"[^)]{0,120}\b" + re.escape(nm) + r"\b", f.src))})
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
		dt_owner = owning_doctype(f)
		e["doctype_owner"] = dt_owner
		e["guard"] = classify_guard(f, d, sinks, perms, ignore_perm, kind, dt_owner)
		e["container_params"] = container_params(f)
		if extra:
			e.update(extra)
		# what the framework can tell us about the doctypes this entry point touches, so a scanner
		# does not have to open every JSON to find out the data is public by design (§6). A child
		# table does not count: reading one without its parent is the A07 finding.
		touched = [dt for dt in e["doctypes_direct"] if dt in doctypes]
		e["doctypes_known"] = touched
		public = "guest_read" if e.get("allow_guest") else "public_read"
		e["touches_only_public_doctypes"] = bool(touched) and all(
			doctypes[dt][public] and not doctypes[dt]["istable"] for dt in touched)
		e["touches_admin_only_doctype"] = [dt for dt in touched if doctypes[dt]["admin_only"]]
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
		"doctype_sources": [os.path.basename(ROOT.rstrip(os.sep))]
		                   + [os.path.basename(x.rstrip(os.sep)) for x in EXTRA_DOCTYPE_ROOTS],
		"doctypes_defined": len(doctypes),
		"doctypes_admin_only": sum(1 for d in doctypes.values() if d["admin_only"]),
		"doctypes_public_read": sum(1 for d in doctypes.values() if d["public_read"]),
		"doctypes_child_tables": sum(1 for d in doctypes.values() if d["istable"]),
		"by_guard_class": dict(sorted(
			(k, sum(1 for e in entries if (e.get("guard") or {}).get("class") == k and not e.get("is_test")))
			for k in {(e.get("guard") or {}).get("class") for e in entries} - {None})),
	}

	def whitelisted(e):
		return e.get("kind", "").startswith("whitelisted")

	def ids(pred):
		return sorted(e["id"] for e in entries
		              if not e.get("is_test") and e.get("guard") and pred(e))

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

		# --- views that narrow to what the framework does NOT guard ----------------------
		# Start here rather than at `no_permission_check`: these are the shapes that survived
		# the refutations in `_framework-guards.md`, so their false positive rate is the lowest
		# in this file.
		"unguarded_db_bypass_write": ids(lambda e: whitelisted(e) and e["guard"]["class"] == "db_bypass_unguarded"),
		"unguarded_unpermissioned_read": ids(lambda e: whitelisted(e) and e["guard"]["class"] == "unpermissioned_read"
		                                     and not e.get("touches_only_public_doctypes")),
		"guest_unguarded_read_or_write": ids(lambda e: e.get("allow_guest")
		                                     and e["guard"]["class"] in ("db_bypass_unguarded", "unpermissioned_read", "ignore_permissions")),
		# §2a: run_doc_method gates read, not write. An instance method that writes is the gap.
		"doc_method_writing_behind_read_gate": ids(lambda e: e.get("kind") == "whitelisted_doctype_method"
		                                           and e["guard"]["class"] == "run_doc_method_read_gate"
		                                           and (e["guard"]["writes_bypassing_document_layer"]
		                                                or e["guard"]["writes_through_document_layer"])),
		# §4a: a document name arriving through a container parameter and deciding authorization
		"container_param_reaching_auth_sink": ids(lambda e: whitelisted(e)
		                                          and any(p["reaches_auth_sink"] for p in e.get("container_params", []))),
		# §3: the query builder's permission switch defaults to off
		"query_builder_unpermissioned": ids(lambda e: whitelisted(e) and e["guard"]["uses_query_builder"]
		                                    and not e["guard"]["query_builder_permissioned"]),
		# §3/§6: these authorize on `select`. Compute their role gap on `select`, never on `read`.
		"select_gated_search_queries": ids(lambda e: e["guard"]["search_input_decorator"]
		                                   or (e["guard"]["uses_query_builder"] and e["guard"]["query_builder_permissioned"])),
		"guest_reaching_doc_load": ids(lambda e: e.get("allow_guest") and "doc_load" in (e.get("sinks_direct") or [])),
	}

	# --- what the framework already guards ------------------------------------------
	# A pattern search flags all of these and the framework covers every one. They are listed
	# with their reason so a scanner can skip them knowingly rather than rediscover them one
	# candidate at a time — and so that overriding one is a deliberate act with a reason to
	# answer. See `_framework-guards.md` §1, §2a and §6.
	refuted = []
	for e in entries:
		if e.get("is_test") or not e.get("guard"):
			continue
		g = e["guard"]
		if g["class"] == "doc_layer_only":
			refuted.append({"id": e["id"], "file": f"{e['file']}:{e['line']}", "rung": "guards §1",
			                "reason": "every write goes through the document layer, which checks permissions itself",
			                "overridable_when": "a document it reads is not the document it writes (§1a), or a caller sets ignore_permissions"})
		elif g["class"] == "unreachable_admin_only_doctype":
			refuted.append({"id": e["id"], "file": f"{e['file']}:{e['line']}", "rung": "guards §2a",
			                "reason": f"run_doc_method read-gates {e.get('doctype_owner')}, which no role but Administrator can read",
			                "overridable_when": "the deployment grants a role read on that doctype — a configuration choice, not a defect"})
		elif whitelisted(e) and e.get("touches_only_public_doctypes") and g["class"] in ("unpermissioned_read", "compute_only"):
			refuted.append({"id": e["id"], "file": f"{e['file']}:{e['line']}", "rung": "guards §6",
			                "reason": "every doctype it reads grants read at permlevel 0 to All or Guest, so every caller of this endpoint is entitled to it by design",
			                "overridable_when": "the response carries a field at permlevel > 0, or rows the caller's user permissions should have scoped"})
	refuted.sort(key=lambda r: r["id"])

	out = {
		"schema": "frappe-endpoint-inventory/2",
		"summary": summary,
		"views": views,
		"refuted_by_framework": refuted,
		"doctypes": doctypes,
		"entry_points": entries,
		"website_routes": routes,
		"socketio_handlers": socket_handlers,
		"socketio_middlewares": mw,
		"api_routes": api_routes,
		"notes": {
			"call_graph_depth": MAXDEPTH,
			"resolution": "callee resolved by simple name across the app; ambiguous names (>6 defs) dropped",
			"sinks_reachable": "union of direct sinks over the transitive callee set",
			"has_permission_check": "regex presence of an explicit permission gate in the entry function or (weaker) its direct callees; presence is not proof of correctness, and ABSENCE IS NOT A FINDING — see guard.class",
			"guard": "how the framework covers this entry point. doc_layer_only and unreachable_admin_only_doctype are non-findings; db_bypass_unguarded and unpermissioned_read are candidates. Read _framework-guards.md before overriding one",
			"doctypes": "permission rows from the DocType JSON in this checkout, resolved at permlevel 0. A live site can carry Custom DocPerm rows that differ, so this is a prior, not the site's answer",
			"external_reference_count": "call sites found by grepping the name. NOT a reachability signal in either direction: a whitelisted dotted path is callable with zero references, and a reference found in a file is not proof that any form or user fires it",
			"container_params": "parameters pydantic does not constrain to a scalar, so an operator payload can still arrive through them. reaches_auth_sink is a proximity match in the body, not dataflow — read the code",
		},
	}
	with open(DEST, "w", encoding="utf-8") as fh:
		json.dump(out, fh, indent=1)
	print(json.dumps(summary, indent=1))


def parse_args():
	global ROOT, APP, DEST, SKIP_DIRS, EXTRA_DOCTYPE_ROOTS
	p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	p.add_argument("output", help="path to write the inventory JSON to")
	p.add_argument("--root", default=os.getcwd(), help="app repository checkout (default: current directory)")
	p.add_argument("--module", help="package inside the checkout holding hooks.py (default: detected)")
	p.add_argument("--skip-dir", action="append", default=[], metavar="NAME",
	               help="extra directory name to skip, repeatable")
	p.add_argument("--doctypes-from", action="append", default=[], metavar="CHECKOUT",
	               help="another app checkout whose DocType permission rows to load, repeatable. "
	                    "The bench's frappe checkout and the target's required_apps are found beside "
	                    "--root automatically; pass this for anything that lives elsewhere: a "
	                    "doctype this builder has not seen cannot refute a finding about it")
	p.add_argument("--no-discover", action="store_true",
	               help="do not look for frappe and required_apps beside --root")
	a = p.parse_args()
	SKIP_DIRS = DEFAULT_SKIP_DIRS | set(a.skip_dir)
	ROOT = os.path.abspath(a.root)
	if not os.path.isdir(ROOT):
		sys.exit(f"Not a directory: {ROOT}")
	APP = os.path.join(ROOT, a.module or detect_app_package(ROOT))
	if not os.path.isdir(APP):
		sys.exit(f"Not a directory: {APP}")
	extra = [os.path.abspath(x) for x in a.doctypes_from if os.path.isdir(x)]
	if not a.no_discover:
		extra += discover_dependency_checkouts(ROOT, APP)
	EXTRA_DOCTYPE_ROOTS = [x for i, x in enumerate(extra) if x not in extra[:i] and x != ROOT]
	is_framework = os.path.basename(APP.rstrip(os.sep)) == "frappe"
	if not is_framework and not any(os.path.basename(x) == "frappe" for x in EXTRA_DOCTYPE_ROOTS):
		print("warning: frappe doctypes not loaded; pass --doctypes-from <bench>/apps/frappe", file=sys.stderr)
	DEST = os.path.abspath(a.output)


parse_args()
main()
