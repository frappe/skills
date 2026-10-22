# API reference: the :name route variable picks one OpenAPI document.


def main(data, CONFIG):
	references = CONFIG["references"]
	name = str(frappe.form_dict.get("name") or "")
	reference = references.get(name) or references[CONFIG["default"]]
	spec = reference["spec"]
	data.title = reference["title"] + " · " + CONFIG["site_title"]
	data.reference_title = reference["title"]
	data.spec_url = spec if spec.startswith("https://") else CONFIG["cdn"] + spec
	data.server = reference.get("server") or ""


main(data, __CONFIG__)
