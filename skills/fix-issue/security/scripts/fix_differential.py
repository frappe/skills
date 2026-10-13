#!/usr/bin/env python3
"""Does a function at a given ref carry a known fix? Answered by a fix differential.

Compares the BODY of one function at each target ref against the same function at
the fix commit and at that commit's parent:

  FIXED      matches the post-fix body
  UNFIXED    matches the pre-fix body
  DIVERGED   neither; reports how many of the lines the fix added are present
  REMOVED    the fix removed the function, and it is absent here too (check that it
             did not move to another file)
  PRESENT    the fix removed the function, but here it exists in another shape
  ABSENT     the file exists but the function does not (the fix may live elsewhere)
  NOFILE     the file does not exist at this ref
  UNPARSED   the file at this ref is not valid Python for this interpreter

Bodies are compared as Python tokens, one logical line at a time, with its
indentation depth. Comments and line wrapping are ignored. String contents are
compared exactly.

It never asks "does this look guarded", because a guard-pattern probe is wrong in
both directions: a fix by a literal argument (ignore_permissions=False) or by
removing the endpoint has no guard call to match, and a guard-shaped token in a
query builder is not a guard.

The fix commit itself is always classified first as a control: it must read FIXED
(REMOVED when the fix removed the function) and its parent UNFIXED. If not, the extractor is broken for this function and every
other verdict is meaningless, so the script exits non-zero. A ref or file it cannot
read (a bad ref, a network or API error) gives no verdict at all: the script stops
with exit code 2, so a failed read is never taken for a missing file.

  # local clone (any remote ref works; nothing is checked out)
  fix_differential.py --git-dir ~/bench/apps/my_app \\
      --path my_app/api.py --func get_member_loans \\
      --fix <sha> upstream/main upstream/version-15

  # a method: qualify it when another class or function has the same name
  fix_differential.py --git-dir ... --path ... --func LoanRequest.approve --fix <sha> ...

  # or straight from GitHub, via the gh CLI
  fix_differential.py --repo <owner>/<app> --path ... --func ... --fix <sha> v1.9.3 main
"""
import argparse, ast, base64, io, json, subprocess, sys, textwrap, tokenize

_CACHE = {}


class ReadError(Exception):
	"""A ref or file that could not be read. Never a verdict: a failed read is not a missing file."""


class AmbiguousName(Exception):
	"""More than one function matches --func. Picking one could compare the wrong body."""


def run(cmd):
	return subprocess.run(cmd, capture_output=True)


def fetch(source, path, ref):
	"""File text at the ref, or None only when the ref exists and the file does not."""
	key = (source, path, ref)
	if key not in _CACHE:
		kind, where = source
		_CACHE[key] = fetch_git(where, path, ref) if kind == "git" else fetch_gh(where, path, ref)
	return _CACHE[key]


def fetch_git(where, path, ref):
	if run(["git", "-C", where, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}"]).returncode:
		raise ReadError(f"ref {ref} not found in {where}")
	r = run(["git", "-C", where, "show", f"{ref}:{path}"])
	if not r.returncode:
		return r.stdout.decode("utf-8", "replace")
	if run(["git", "-C", where, "cat-file", "-e", f"{ref}:{path}"]).returncode:
		return None
	raise ReadError(f"cannot read {path} at {ref}: {r.stderr.decode().strip()}")


def fetch_gh(where, path, ref):
	r = run(["gh", "api", f"/repos/{where}/contents/{path}?ref={ref}"])
	if r.returncode:
		# A 404 means a missing file only when the ref itself resolves.
		if "HTTP 404" in r.stderr.decode() and not run(["gh", "api", f"/repos/{where}/commits/{ref}"]).returncode:
			return None
		raise ReadError(f"cannot read {path} at {ref}: {r.stderr.decode().strip()}")
	try:
		d = json.loads(r.stdout)
	except json.JSONDecodeError:
		raise ReadError(f"unexpected response for {path} at {ref}")
	if d.get("encoding") != "base64":
		raise ReadError(f"{path} at {ref} is not a file the contents API returns in full")
	return base64.b64decode(d["content"]).decode("utf-8", "replace")


def qualified_defs(tree):
	"""(qualified name, node) for every function: `func`, `Class.method` or `outer.inner`."""
	found = []

	def visit(node, prefix):
		for child in ast.iter_child_nodes(node):
			if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
				name = f"{prefix}{child.name}"
				if not isinstance(child, ast.ClassDef):
					found.append((name, child))
				visit(child, name + ".")
			else:
				visit(child, prefix)

	visit(tree, "")
	return found


def extract(src, func):
	"""Source of the one function named `func` (plain or qualified), decorators included."""
	matches = [(name, node) for name, node in qualified_defs(ast.parse(src)) if func in (name, node.name)]
	if not matches:
		return None
	if len(matches) > 1:
		names = ", ".join(name for name, _ in matches)
		raise AmbiguousName(f"--func {func} matches {names}; pass the qualified name")
	node = matches[0][1]
	# A decorator's lineno is that of its expression, which starts on the `@` line.
	start = min([node.lineno] + [d.lineno for d in node.decorator_list])
	return "\n".join(src.split("\n")[start - 1 : node.end_lineno])


def body(source, path, func, ref):
	src = fetch(source, path, ref)
	if src is None:
		return None, "NOFILE"
	try:
		b = extract(src, func)
	except SyntaxError:
		return None, "UNPARSED"
	return (b, "OK") if b is not None else (None, "ABSENT")


def norm(text):
	"""Logical lines as (depth, tokens). Comments and wrapping drop out; strings stay exact."""
	skip = {tokenize.COMMENT, tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER}
	out, line, depth = [], [], 0
	if text is None:
		return out
	for tok in tokenize.generate_tokens(io.StringIO(textwrap.dedent(text)).readline):
		if tok.type == tokenize.INDENT:
			depth += 1
		elif tok.type == tokenize.DEDENT:
			depth -= 1
		elif tok.type == tokenize.NEWLINE:
			if line:
				out.append((depth, tuple(line)))
			line = []
		elif tok.type not in skip:
			line.append(tok.string)
	if line:
		out.append((depth, tuple(line)))
	return out


def classify(source, func, fix, ref, path, fix_path):
	post, st_post = body(source, fix_path, func, fix)
	pre, _ = body(source, fix_path, func, fix + "~1")
	tgt, st_tgt = body(source, path, func, ref)
	removal = fix_removes(source, func, fix, fix_path)
	if st_post != "OK" and not removal:
		return {"verdict": "NOBASE", "note": f"{func} not found in {fix_path} at {fix} or its parent"}
	if removal and st_tgt in ("ABSENT", "NOFILE"):
		return {"verdict": "REMOVED"}
	if st_tgt != "OK":
		return {"verdict": st_tgt}
	n_pre, n_tgt = norm(pre), norm(tgt)
	if removal:
		return {"verdict": "UNFIXED" if n_tgt == n_pre else "PRESENT"}
	n_post = norm(post)
	if n_tgt == n_post:
		return {"verdict": "FIXED"}
	if pre is not None and n_tgt == n_pre:
		return {"verdict": "UNFIXED"}
	added = [l for l in n_post if l not in n_pre]
	carried = [l for l in added if l in n_tgt]
	return {
		"verdict": "DIVERGED",
		"added": len(added),
		"carried": len(carried),
		"missing": [" ".join(tokens) for depth, tokens in added if (depth, tokens) not in n_tgt][:6],
	}


def fix_removes(source, func, fix, fix_path):
	_, st_post = body(source, fix_path, func, fix)
	_, st_pre = body(source, fix_path, func, fix + "~1")
	return st_post in ("ABSENT", "NOFILE") and st_pre == "OK"


def main():
	try:
		report(parse_args())
	except ReadError as e:
		print(f"read failed, no verdict: {e}", file=sys.stderr)
		sys.exit(2)
	except AmbiguousName as e:
		print(f"no verdict: {e}", file=sys.stderr)
		sys.exit(2)


def parse_args():
	p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	g = p.add_mutually_exclusive_group(required=True)
	g.add_argument("--git-dir", help="local clone to read refs from")
	g.add_argument("--repo", help="owner/name on GitHub, read through the gh CLI")
	p.add_argument("--path", required=True, help="file path on the TARGET refs")
	p.add_argument("--fix-path", help="file path at the fix commit, if it moved")
	p.add_argument("--func", required=True, help="function name, or Class.method when the name repeats")
	p.add_argument("--fix", required=True, help="sha of the commit that fixed it")
	p.add_argument("refs", nargs="*")
	return p.parse_args()


def report(a):
	source = ("git", a.git_dir) if a.git_dir else ("gh", a.repo)
	fix_path = a.fix_path or a.path

	fixed = "REMOVED" if fix_removes(source, a.func, a.fix, fix_path) else "FIXED"
	control = [
		(a.fix, classify(source, a.func, a.fix, a.fix, fix_path, fix_path), fixed),
		(a.fix + "~1", classify(source, a.func, a.fix, a.fix + "~1", fix_path, fix_path), "UNFIXED"),
	]
	broken = False
	for ref, r, want in control:
		ok = r["verdict"] == want
		broken |= not ok
		print(f"control {ref:22} {r['verdict']:9} {'ok' if ok else 'EXPECTED ' + want}")
	if broken:
		print("\ninstrument failed its control; no verdict below would mean anything", file=sys.stderr)
		post, _ = body(source, fix_path, a.func, a.fix)
		pre, _ = body(source, fix_path, a.func, a.fix + "~1")
		if post is not None and norm(post) == norm(pre):
			print(
				f"the fix does not change {a.func}: for a change outside it (an import, a constant),"
				" use the hunk check in verify.md step 2",
				file=sys.stderr,
			)
		sys.exit(1)
	print()

	for ref in a.refs:
		r = classify(source, a.func, a.fix, ref, a.path, fix_path)
		extra = ""
		if r["verdict"] == "DIVERGED":
			extra = f"  carries {r['carried']}/{r['added']} of the fix's added lines"
		print(f"{ref:30} {r['verdict']:9}{extra}")
		if r["verdict"] == "REMOVED":
			print(f"{'':32}confirm {a.func} did not move to another file at this ref")
		elif r["verdict"] == "PRESENT":
			print(f"{'':32}the fix removed {a.func}, but it exists here in another shape: read it")
		for line in r.get("missing", []):
			print(f"{'':32}missing: {line}")


if __name__ == "__main__":
	main()
