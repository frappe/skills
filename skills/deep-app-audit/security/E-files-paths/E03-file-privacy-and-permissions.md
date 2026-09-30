---
id: E03
area: files-paths
---
# E03 — File privacy defaults and access control

**Scope:** the `File` doctype and everything that creates attachments.

**Why:** private files leak through predictable names, missing permission checks, and attachment
enumeration through naming series.

## Find
- Default value of `is_private` at every creation path: `save_file`, the upload API, frappe-ui
  uploaders, web forms, portal attachments, email attachment ingestion. Public-by-default
  recurs across apps.
- `File.has_permission` and `has_website_permission`: does reading a file check permission on
  its `attached_to_doctype` / `attached_to_name`?
- Write and delete permission on `File` — can a user detach or overwrite someone else's file?
- URL guessability for public files, and enumeration of `attached_to_name` via naming series.
- Endpoints that return file content directly (`get_file_content`, embed/preview handlers) —
  check that they apply `File` permissions.

## Confirm
- Test the case of a file attached to a document the caller cannot read.

## Report
List the creation paths that default to public.
