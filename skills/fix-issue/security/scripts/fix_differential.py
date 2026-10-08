#!/usr/bin/env python3
"""Does a function at a given ref carry a known fix? Answered by a fix differential.

Compares the BODY of one function at each target ref against the same function at
the fix commit and at that commit's parent:

  FIXED      matches the post-fix body
  UNFIXED    matches the pre-fix body verbatim
  DIVERGED   neither; reports how many of the lines the fix added are present
  ABSENT     the file exists but the function does not (the fix may live elsewhere)
  NOFILE     the file does not exist at this ref

It never asks "does this look guarded", because a guard-pattern probe is wrong in
both directions: a fix by a literal argument (ignore_permissions=False) or by
removing the endpoint has no guard call to match, and a guard-shaped token in a
query builder is not a guard.

The fix commit itself is always classified first as a control: it must read FIXED
and its parent UNFIXED. If not, the extractor is broken for this function and every
other verdict is meaningless, so the script exits non-zero.

  # local clone (any remote ref works; nothing is checked out)
  fix_differential.py --git-dir ~/bench/apps/my_app \\
      --path my_app/api.py --func get_member_loans \\
      --fix <sha> upstream/main upstream/version-15

  # or straight from GitHub, via the gh CLI
  fix_differential.py --repo <owner>/<app> --path ... --func ... --fix <sha> v1.9.3 main
"""
import argparse, base64, json, re, subprocess, sys

_CACHE = {}


def fetch(source, path, ref):
	key = (source, path, ref)
	if key in _CACHE:
		return _CACHE[key]
	kind, where = source
	out = None
	if kind == "git":
		r = subprocess.run(["git", "-C", where, "show", f"{ref}:{path}"], capture_output=True)
		if not r.returncode:
			out = r.stdout.decode("utf-8", "replace")
	else:
		r = subprocess.run(["gh", "api", f"/repos/{where}/contents/{path}?ref={ref}"], capture_output=True)
		if not r.returncode:
			try:
				d = json.loads(r.stdout)
				if "content" in d:
					out = base64.b64decode(d["content"]).decode("utf-8", "replace")
			except json.JSONDecodeError:
				pass
	_CACHE[key] = out
	return out


def extract(src, func):
	"""Source of `def func` at any indentation (so methods are found), decorators included."""
	lines = src.split("\n")
	pat = re.compile(rf"^(\s*)(?:async\s+)?def\s+{re.escape(func)}\s*\(")
	for i, line in enumerate(lines):
		m = pat.match(line)
		if not m:
			continue
		indent = len(m.group(1))
		start = i
		while start > 0 and lines[start - 1].lstrip().startswith("@"):
			start -= 1
		# Step past the whole signature first: a multi-line signature closes with
		# `) -> X:` at the def's own indent, and a naive dedent scan stops there.
		depth, sig_end = 0, i
		for j in range(i, len(lines)):
			depth += lines[j].count("(") - lines[j].count(")")
			if depth <= 0 and lines[j].rstrip().endswith(":"):
				sig_end = j
				break
		end = sig_end + 1
		while end < len(lines):
			s = lines[end]
			if s.strip() and (len(s) - len(s.lstrip())) <= indent:
				break
			end += 1
		return "\n".join(lines[start:end])
	return None


def body(source, path, func, ref):
	src = fetch(source, path, ref)
	if src is None:
		return None, "NOFILE"
	b = extract(src, func)
	return (b, "OK") if b is not None else (None, "ABSENT")


def norm(text):
	out = []
	for ln in (text or "").split("\n"):
		ln = re.sub(r"#.*$", "", ln).strip()
		if ln:
			out.append(re.sub(r"\s+", " ", ln))
	return out


def classify(source, func, fix, ref, path, fix_path):
	post, st_post = body(source, fix_path, func, fix)
	pre, _ = body(source, fix_path, func, fix + "~1")
	tgt, st_tgt = body(source, path, func, ref)
	if st_post != "OK":
		return {"verdict": "NOBASE", "note": f"{func} not found in {fix_path} at {fix}"}
	if st_tgt != "OK":
		return {"verdict": st_tgt}
	n_post, n_pre, n_tgt = norm(post), norm(pre), norm(tgt)
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
		"missing": [l for l in added if l not in n_tgt][:6],
	}


def main():
	p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	g = p.add_mutually_exclusive_group(required=True)
	g.add_argument("--git-dir", help="local clone to read refs from")
	g.add_argument("--repo", help="owner/name on GitHub, read through the gh CLI")
	p.add_argument("--path", required=True, help="file path on the TARGET refs")
	p.add_argument("--fix-path", help="file path at the fix commit, if it moved")
	p.add_argument("--func", required=True)
	p.add_argument("--fix", required=True, help="sha of the commit that fixed it")
	p.add_argument("refs", nargs="*")
	a = p.parse_args()

	source = ("git", a.git_dir) if a.git_dir else ("gh", a.repo)
	fix_path = a.fix_path or a.path

	control = [
		(a.fix, classify(source, a.func, a.fix, a.fix, fix_path, fix_path), "FIXED"),
		(a.fix + "~1", classify(source, a.func, a.fix, a.fix + "~1", fix_path, fix_path), "UNFIXED"),
	]
	broken = False
	for ref, r, want in control:
		ok = r["verdict"] == want
		broken |= not ok
		print(f"control {ref:22} {r['verdict']:9} {'ok' if ok else 'EXPECTED ' + want}")
	if broken:
		print("\ninstrument failed its control; no verdict below would mean anything", file=sys.stderr)
		sys.exit(1)
	print()

	for ref in a.refs:
		r = classify(source, a.func, a.fix, ref, a.path, fix_path)
		extra = ""
		if r["verdict"] == "DIVERGED":
			extra = f"  carries {r['carried']}/{r['added']} of the fix's added lines"
		print(f"{ref:30} {r['verdict']:9}{extra}")
		for line in r.get("missing", []):
			print(f"{'':32}missing: {line}")


if __name__ == "__main__":
	main()
