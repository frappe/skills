"""Run a generated data script locally the way Frappe's safe_exec would (with server scripts on).

    python build.py SPEC.json --emit out/
    python sandbox.py out/doc-page.data_script.py --route /docs/compute/placement --block out/doc-page.json
    python sandbox.py out/page-home.data_script.py --page
    python sandbox.py out/page-api-reference_name.data_script.py --page --form name=atlas

Same compile policy (RestrictedPython) and the same builtins as the site, so a NameError or a
policy error shows here instead of as a 500. frappe.make_get_request and md_to_html are real
(urllib, markdown2 with Frappe's extras); frappe.db.get_all returns the --block definition.
"""

from __future__ import annotations

import argparse
import json
import operator
import types
import urllib.request

import markdown2
from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import guarded_iter_unpack_sequence

# frappe.utils.safe_exec: RestrictedPython safe_builtins plus get_python_builtins().
FRAPPE_EXTRA = ["abs", "all", "any", "bool", "dict", "enumerate", "isinstance", "issubclass", "list", "max", "min", "range", "set", "sorted", "sum", "tuple"]
MD_EXTRAS = {"fenced-code-blocks": None, "tables": None, "header-ids": None, "toc": None, "highlightjs-lang": None, "html-classes": {"table": "table table-bordered", "img": "screenshot"}}


class Dict(dict):
	__getattr__ = dict.get

	def __setattr__(self, key, value):
		self[key] = value


def get_request(url: str):
	"""Frappe's make_request: text/plain; charset=utf-8 comes back as parse_qs, JSON parsed."""
	with urllib.request.urlopen(url, timeout=60) as response:
		body = response.read().decode()
		kind = response.headers.get("content-type", "")
	if kind == "text/plain; charset=utf-8":
		raise SystemExit(f"{url} is text/plain; Frappe would return parse_qs(...) instead of the text")
	return json.loads(body) if kind.split(";")[0].endswith("json") else body


def run(path: str, route: str, block: dict | None, page: bool, form: dict) -> dict:
	builtins = dict(safe_builtins)
	builtins.update({name: getattr(__builtins__, name, None) or __builtins__[name] for name in FRAPPE_EXTRA})
	guards = {
		"__builtins__": builtins,
		"_getattr_": getattr,
		"_getitem_": default_guarded_getitem,
		"_getiter_": default_guarded_getiter,
		"_write_": lambda obj: obj,
		"_iter_unpack_sequence_": guarded_iter_unpack_sequence,
		"_inplacevar_": lambda op, a, b: {"+=": operator.iadd, "-=": operator.isub}[op](a, b),
	}
	code = compile_restricted(open(path).read(), filename=path, mode="exec")
	parts = [part for part in route.strip("/").split("/")[1:] if part]
	form_dict = Dict({**{f"p{index + 1}": value for index, value in enumerate(parts)}, **form})
	frappe = types.SimpleNamespace(
		make_get_request=get_request,
		form_dict=form_dict,
		utils=types.SimpleNamespace(md_to_html=lambda text: markdown2.markdown(text or "", extras=MD_EXTRAS)),
		db=types.SimpleNamespace(get_all=lambda *args, **kwargs: [{"block": json.dumps(block)}] if block else []),
	)
	result = Dict()
	local = {"data": result} if page else {"props": Dict(), "component": result}
	exec(code, {**guards, "frappe": frappe, "json": json}, local)
	return result


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("script")
	parser.add_argument("--route", default="/")
	parser.add_argument("--block", help="the component definition JSON (for the reading order)")
	parser.add_argument("--page", action="store_true", help="a page data script (fills data, not component)")
	parser.add_argument("--form", action="append", default=[], help="extra form_dict values, key=value")
	args = parser.parse_args()
	block = json.load(open(args.block)) if args.block else None
	form = dict(item.split("=", 1) for item in args.form)
	result = run(args.script, args.route, block, args.page, form)
	for key, value in result.items():
		if isinstance(value, str) and len(value) > 120:
			value = f"<{len(value)} chars>"
		elif key == "outline":
			value = [entry["text"] for entry in value]
		print(f"{key}: {value}")


if __name__ == "__main__":
	main()
