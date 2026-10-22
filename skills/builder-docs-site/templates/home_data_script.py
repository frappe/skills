# Home page body: the home Markdown from the repository, below the Builder hero.
# Needs server scripts enabled (frappe.utils.md_to_html). A def can't see top-level names.


def main(data, CONFIG):
	markdown = frappe.make_get_request(CONFIG["cdn"] + CONFIG["home_source"]) or ""
	if markdown.startswith("---"):
		closing = markdown.find("\n---", 3)
		if closing > 0:
			markdown = markdown[closing + 4 :]
	html = frappe.utils.md_to_html(markdown) or ""
	# Links in the home Markdown are relative to the repository root; pages live under /<prefix>.
	docs_dir = CONFIG["docs_dir"]
	prefix = CONFIG["prefix"]
	for start in ['href="./', 'href="']:
		if docs_dir:
			html = html.replace(start + docs_dir + "/", 'href="/' + prefix + "/")
	html = html.replace('/" ', '" ').replace('/">', '">')
	data.title = CONFIG["site_title"]
	data.home_html = html


main(data, __CONFIG__)
