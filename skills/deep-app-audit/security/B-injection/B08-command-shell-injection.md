# B08 — Command and shell injection

**Scope:** process execution with non-literal arguments.

**Why:** commands built by string concatenation, for example database index management, run with
bench privileges.

## Find
- `rg -n "subprocess|os\.system|os\.popen|commands\.|shell=True|check_output|Popen" --type py`
- `frappe.utils.execute_in_shell`, bench command wrappers, deployment scripts, backup and
  restore paths, `mysqldump`/`mysql`/`tar`/`gzip`/`wkhtmltopdf`/`chromium` invocations.
- Anything building a command string with an f-string.
- Filenames, site names, database names, table/index names taken from a request and passed to
  a shell.

## Confirm
- `shell=True` plus any interpolation is a finding. A list-argument `Popen` without
  `shell=True` is usually safe unless the binary itself takes a dangerous option (`--config`,
  `-o`, `@file`) — check for argument injection too.

## Report
Include the metacharacter that breaks out.
