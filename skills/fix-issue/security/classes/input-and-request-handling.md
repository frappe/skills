# Fix request handling on a whitelisted endpoint

**Every argument of a whitelisted function is attacker input, and so is the HTTP verb.** Frappe
checks the CSRF token only on unsafe methods, annotations check types but not values, and a function
with no `methods=` answers GET. Each fix below closes one of those gaps at the function's signature or
its first lines.

## Steps

### 1. Restrict the verb

If the body changes state — `insert`, `save`, `submit`, `db_set`, `db.set_value`, `delete`, a
`frappe.db.commit()`, `sendmail`, `enqueue`, an external call — declare the verb:

```python
@frappe.whitelist(methods=["POST"])          # or ["POST", "PUT"], ["POST", "DELETE"]
def approve(...):
```

Frappe validates the CSRF token only for POST/PUT/DELETE/PATCH, and the session cookie is
`SameSite=Lax`, which a cross-site top-level GET still carries. So a state change reachable over GET
can be forged from any site. GET requests are rolled back at the end, but an explicit commit, an
email, a queued job or an external call has already happened.

Decide from what the body does, not its name: a `make_*` that builds a document in memory and
returns it is correctly plain `@frappe.whitelist()`.

If a GET page renders a confirmation form, put `frappe.sessions.get_csrf_token()` in it and make the
action POST-only.

Done when: every state-changing whitelisted function in scope declares `methods=`, and every JS
caller (`frappe.call` defaults to POST. Check `frappe.xcall` and any `type: "GET"`) still works.

### 2. Validate values, not just types

Annotations on whitelisted arguments are checked by `typing_validations`, with gaps that matter:

- **A string-valued `Literal["asc", "desc"]` is never validated.** The check that skips forward
  references sees the Literal's values as strings and skips it. (`Literal[1, 2]` and
  `Literal["a"] | None` are validated.) Re-check the value in the body.
- **`doctype: str` accepts any DocType. `limit: int` accepts any integer.** Allow-list the value:
  `if args.dt not in ALLOWED_DOCTYPES: frappe.throw(...)`.
- **`filters: dict` guarantees only the container.** `filters["name"] = ["like", "%"]` widens a query
  after one record was authorised. Coerce a name to a scalar — `cstr(name)` or
  `isinstance(name, str)` — before any lookup.

An endpoint that does all of it:

```python
ALLOWED_DOCTYPES = ("Order", "Invoice")

@frappe.whitelist(methods=["POST"])
def make_request(dt: str, dn: str):
	if dt not in ALLOWED_DOCTYPES:
		frappe.throw(_("Invalid DocType"))
	if not isinstance(dn, str):
		frappe.throw(_("Invalid name"))
	frappe.has_permission("Request", "create", throw=True)        # the action
	frappe.has_permission(dt, "read", doc=dn, throw=True)         # the referenced record
	...
```

Done when: every argument that selects a record, a DocType, a field, a sort key or an operation is
checked against a closed set or coerced to a scalar before use.

### 3. Close mass assignment and bypass flags

- **Fix the DocType and the fields in code.** Replace
  `frappe.get_doc({"doctype": "Contact Request", **payload})` with `frappe.new_doc("Contact Request")` and copy an
  explicit field allow-list.
- **Normalise first, then check every key.** A `fieldname` parameter that may be a string, a dict or
  a JSON string must be parsed into a dict before checking it against forbidden fields
  (`frappe.model.default_fields`, `child_table_fields`). A check that runs before parsing is defeated
  by a dict.
- **Remove caller-controlled bypass flags.** A whitelisted signature or `form_dict` that can set
  `ignore_permissions`, `flags.ignore_permissions` or similar is a privilege switch:
  `args.pop("ignore_permissions", None)`, then add the real check
  (`frappe.has_permission(<DocType>, "create", throw=True)`). Where an inner helper takes the flag,
  pass a literal `False`.
- **Enforce on the server every limit the UI applies.** The server sees the request, not the dialog.

Done when: no request value can name the DocType, a non-allow-listed field, or a permission bypass.

### 4. Rate-limit guest endpoints that send mail or create records

```python
from frappe.rate_limiter import rate_limit

@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=get_limit_from_settings, seconds=60 * 60)
def request_thing(email: str):
	...
	return _("If an account with this email exists, instructions have been sent.")
```

Put `@rate_limit` under `@frappe.whitelist`. `limit` may be a callable that reads a setting. Return
the same response whether or not the identity exists — see
[classes/auth-and-disclosure.md](auth-and-disclosure.md) for enumeration.

Done when: limit + 1 requests from one IP get `RateLimitExceededError` (HTTP 429).

### 5. Verify

- **Verb:** GET → refused by `is_valid_http_method`. POST without `X-Frappe-CSRF-Token` →
  `CSRFTokenError`. The real UI action still succeeds.
- **Shape probes for every argument:** a dict, a list, `""`, a JSON string, an out-of-allow-list value,
  and an out-of-`Literal` value. Expect a clean refusal — not a 500, not wider data. A crash that
  happens to stop the leak (`AttributeError` on a list) is not a boundary.
- **As a Website User over real HTTP**: authenticated, so the whitelist gate never stops them. Only
  your checks do.
- **The legitimate call**: same result before and after.

Done when, on every release line: each probe got through on the pre-fix code (the known-positive
control, [verify.md](../verify.md)) and is refused by the
fix.

## References

- Shipping, backports and the public PR: [the security workflow](../workflow.md).
