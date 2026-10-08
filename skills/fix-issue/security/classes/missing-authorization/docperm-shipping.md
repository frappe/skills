# Shipping the DocPerm rows a guard needs

A new permission check denies every role that lacks the checked ptype. The rows that keep the
legitimate callers working ship **in the same PR as the check**, in this order: rows, then the patch
that delivers them to customised sites, then the check. Splitting them makes the check commit a
standalone regression.

## 1. JSON rows, and the `modified` bump

Edit the DocType's `.json` `permissions` array. Grant the ptype the guard checks — a `select` guard
needs a `select` row, a `read` guard a `read` row — to the roles with write or create on the calling
form.

**Bump the DocType's `modified` to the current datetime in the same edit.** `frappe.modules.import_file`
compares timestamps and skips the re-import when they match, so without a bump the row silently never
lands on a site that has already migrated. Take the value from the clock at the moment you edit, in
frappe's format, rather than typing a round time:

```bash
python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))"
```

```diff
- "modified": "2024-04-07 11:26:42.021585",
+ "modified": "2026-10-07 23:52:18.403117",
```

If you migrated a test site mid-work, or the JSON is edited again later, bump it again to the new
current datetime: the value must be later than anything any site has already imported. On every
release line, use that line's own current datetime when the edit lands there.

## 2. Why the JSON rows are not enough: Custom DocPerm

Frappe reads a DocType's shipped `DocPerm` rows **only while it has no `Custom DocPerm` row**. The
first edit in Role Permission Manager calls `copy_perms`, which snapshots every row into `Custom
DocPerm`; from then on, rows you ship never reach that site. `add_permission` and
`update_permission_property` call `setup_custom_perms` → `copy_perms` too, so even calling them from
code switches the DocType to custom permissions — and detaches it from all future JSON permission
changes, including tightenings.

So the delivery for customised sites is a **mirror patch**, and it runs **only for DocTypes that
already have Custom DocPerm rows**.

## 3. Mirror-patch rules

1. **Skip DocTypes that are not customised:**
   `if not frappe.db.exists("Custom DocPerm", {"parent": doctype}): continue`. They read the JSON
   already, and inserting would switch them to custom permissions.
2. **Insert only where the (DocType, role, permlevel 0) pair has no rule at all.** An existing row that
   grants neither `read` nor `select` is an administrator's decision. Leave it.
3. **Skip a pair the site removed or edited.** That shows as a `Permission Log` row with
   `reference_type="Custom DocPerm"`, `for_document=<doctype>` and `status in ("Removed", "Updated")`.
   The role is inside its `changes` JSON. If the `Permission Log` DocType does not exist on that
   version, skip the patch — a deleted rule would look like one that never existed.
4. **Write every ptype explicitly.** `Custom DocPerm` defaults `read` and `export` to 1, so a bare
   `{"select": 1}` insert also grants read and export.
5. **Widen an existing row only when it is an exact copy of the previous release's shipped row** and
   the site has not changed it. A row `copy_perms` copied unchanged is a release rule, not an admin
   choice.
6. **Removing an over-broad shipped row** (for example an `All` row) on customised sites is
   unconditional — it is the exposure being closed.
7. **One savepoint per row**, and roll back before `frappe.log_error`: on Postgres a failed statement
   leaves the transaction unusable, so the log write fails too.
8. Frappe skips its own `Permission Log` entry during migrate, so write an "Added" log row yourself
   if administrators should see the change.
9. `frappe.clear_cache(doctype=dt)` after any change.
10. **Never read `frappe.get_meta(dt).permissions` in a patch or install.** `Meta` skips custom
    permissions while `in_patch` or `in_install` is set, so it returns the *shipped* rows — and caches
    them. Read the site's real rows with `frappe.permissions.get_all_perms(role)` and
    `frappe.permissions.get_doctypes_with_custom_docperms()`.

```python
def get_role_rules(doctype, role):
	# get_meta reads only shipped rules during a patch; get_all_perms reads the site's.
	rules = []
	for rule in get_all_perms(role):
		if rule.parent == doctype:
			rules.append(rule)
	return rules
```

## 4. A row on a DocType another app ships

When the DocType belongs to another app (Address is shipped by frappe), you cannot ship the row in
JSON. Put a function in your app's `setup/install.py`, call it from `after_install`, and add it to
`patches.txt` as an `execute:` line so upgrading sites run it once:

```
execute:from myapp.setup.install import grant_address_read_to_my_role; grant_address_read_to_my_role()
```

```python
def grant_address_read_to_my_role():
	if not frappe.db.exists("Role", ROLE):
		return
	if get_role_rules(DOCTYPE, ROLE):           # any rule: keep the site's decision
		return
	if site_changed_rule(DOCTYPE, ROLE):        # Permission Log Removed/Updated
		return
	add_permission(DOCTYPE, ROLE, 0, "read")
	update_permission_property(DOCTYPE, ROLE, 0, "export", 0)   # add_permission turns export on
	frappe.clear_cache(doctype=DOCTYPE)
```

Keep setup code free of imports from `patches/`. Patches import from `setup`, not the reverse.

If the row needs a change *inside* the other app's repository, and that change will not ship first,
**do not ship the check.**

## 5. Prove the rows land

On a **pre-fix site with the DocType customised** (so Custom DocPerm rows exist), check out the fix
and run a real `bench migrate` — not `reload_doc`. Confirm the patch in `Patch Log` by creation time,
then confirm each loser now holds the ptype with `frappe.permissions.get_all_perms(role)`. A fresh
site proves only the JSON half.
