"""A small DSL for Builder block trees: blocks, bindings, props, component instances.

Shapes follow the frappe-builder skill's reference (blocks.md, components.md).
"""

from __future__ import annotations

import copy
import hashlib
import json
import secrets

# attributes holds the standard ones; everything else (data-*, aria-*, role, id) is customAttributes.
STANDARD_ATTRIBUTES = {"src", "darkSrc", "alt", "href", "target", "rel", "placeholder", "type", "value", "title"}
SOURCES = {"props": "props", "component": "componentData", "data": "dataScript"}
PRIMARY = {"img": "src", "a": "href"}

# Component definitions by id, for building instance skeletons.
DEFINITIONS: dict[str, dict] = {}


def source(expression: str) -> dict:
	head, _, key = expression.partition(".")
	return {"key": key, "comesFrom": SOURCES[head]}


def binding_type(prop: str) -> str:
	if prop == "innerHTML":
		return "key"
	if prop in STANDARD_ATTRIBUTES or prop.startswith(("data-", "aria-")):
		return "attribute"
	return "style"


def block(
	element: str = "div",
	style: dict | None = None,
	children: list | None = None,
	*,
	name: str = "",
	classes: list[str] | None = None,
	attrs: dict | None = None,
	mobile: dict | None = None,
	tablet: dict | None = None,
	text: str | None = None,
	bind: dict | None = None,
	visible_if: str | None = None,
	repeat: str | None = None,
	props: dict | None = None,
	js: str | None = None,
	css: str | None = None,
	raw_html: bool = False,
) -> dict:
	"""One block. `bind` maps a property (innerHTML, href, data-x, a style) to props.x,
	component.x or data.x; the first innerHTML/src/href binding is the block's dataKey."""
	node = {
		"blockId": "",
		"element": element,
		"blockName": name,
		"baseStyles": dict(style or {}),
		"mobileStyles": dict(mobile or {}),
		"tabletStyles": dict(tablet or {}),
		"attributes": {},
		"customAttributes": {},
		"classes": list(classes or []),
		"children": list(children or []),
	}
	for key, value in (attrs or {}).items():
		node["attributes" if key in STANDARD_ATTRIBUTES else "customAttributes"][key] = value
	if text is not None:
		node["innerHTML"] = text
	if raw_html:
		node["originalElement"] = "__raw_html__"
	if repeat:
		node["isRepeaterBlock"] = True
		node["dataKey"] = source(repeat)
	if bind:
		primary = "innerHTML" if "innerHTML" in bind else PRIMARY.get(element)
		node["dynamicValues"] = []
		for prop, expression in bind.items():
			entry = {**source(expression), "type": binding_type(prop), "property": prop}
			if prop == primary and not repeat:
				node["dataKey"] = entry
			else:
				node["dynamicValues"].append(entry)
	if visible_if:
		node["visibilityCondition"] = source(visible_if)
	if props:
		node["props"] = {key: declare(key, spec) for key, spec in props.items()}
	if js or css:
		node["clientScript"] = {key: value for key, value in (("js", js), ("css", css)) if value}
	return node


def text(element: str, content: str, style: dict | None = None, **options) -> dict:
	return block(element, style, text=content, **options)


def body(children: list, style: dict | None = None) -> dict:
	"""The page root. originalElement "body" keeps the page's scripts, page_data and CSRF token."""
	root = block("div", {"display": "flex", "flexDirection": "column", "alignItems": "center", "flexWrap": "wrap", "flexShrink": 0, **(style or {})}, children, name="Body")
	root["blockId"] = "root"
	root["originalElement"] = "body"
	return root


def prop(kind: str, default=None, *, label: str = "") -> dict:
	return {"type": kind, "default": default, "label": label}


def declare(name: str, spec: dict) -> dict:
	kind, default = spec["type"], spec.get("default")
	if kind == "boolean":
		options = {"defaultValue": "true" if str(default).lower() in ("true", "1") else "false", "trueLabel": "Yes", "falseLabel": "No"}
	else:
		options = {"defaultValue": "" if default is None else default}
	return {
		"label": spec.get("label") or name.replace("_", " ").title(),
		"isStandard": True,
		"isDynamic": False,
		"isPassedDown": True,
		"comesFrom": None,
		"value": None,
		"propOptions": {"type": kind, "isRequired": False, "options": options, "dependencies": {}},
	}


def skeleton(children: list, owner: str) -> list:
	"""Instance-side refs mirroring the definition's children (the server renders through them)."""
	refs = []
	for child in children:
		ref = {"blockId": secrets.token_hex(4), "referenceBlockId": child["blockId"], "isChildOfComponent": owner, "children": skeleton(child.get("children") or [], owner)}
		if child.get("isRepeaterBlock"):
			ref["isRepeaterBlock"] = True
		refs.append(ref)
	return refs


def instance(component_id: str, *, style: dict | None = None, props: dict | None = None) -> dict:
	definition = DEFINITIONS[component_id]
	root = block(definition["element"], style, skeleton(definition.get("children") or [], component_id), name=definition.get("blockName", ""))
	root["blockId"] = secrets.token_hex(4)
	root["extendedFromComponent"] = component_id
	if props:
		declared = definition.get("props") or {}
		root["props"] = {key: {**copy.deepcopy(declared[key]), "value": value} for key, value in props.items()}
	return root


def stabilize_ids(root: dict, component_id: str) -> dict:
	"""Ids from the component id and each block's name path, so a rebuilt definition keeps the
	ids that page skeletons reference. Repeated sibling names get #2, #3."""

	def assign(node: dict, path: str) -> None:
		if not node.get("blockId"):
			node["blockId"] = hashlib.sha1(f"{component_id}:{path}".encode()).hexdigest()[:8]
		seen: dict[str, int] = {}
		for index, child in enumerate(node.get("children") or []):
			label = child.get("blockName") or str(index)
			seen[label] = seen.get(label, 0) + 1
			assign(child, f"{path}/{label}" + (f"#{seen[label]}" if seen[label] > 1 else ""))

	assign(root, "")
	return root


def normalize(tree: dict) -> dict:
	"""Give every block, skeleton refs included, an id and the empty fields Builder expects.
	Page trees get random ids; definitions get stable ones from stabilize_ids first."""
	if not tree.get("blockId"):
		tree["blockId"] = secrets.token_hex(4)
	for key in ("baseStyles", "mobileStyles", "tabletStyles", "attributes", "customAttributes"):
		tree.setdefault(key, {})
	tree.setdefault("classes", [])
	tree.setdefault("children", [])
	for child in tree["children"]:
		normalize(child)
	return tree


def compact_json(value) -> str:
	return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
