# Fix authentication and disclosure flaws in a Frappe app

Two questions decide every fix in this class. **Who does the server believe the caller is, and on
what evidence?** And **what does each response tell a caller who should learn nothing?**

## Steps

### 1. Authentication: trust the session, not the request

| Shape | Fix |
|---|---|
| A guest endpoint calls `frappe.set_user(user)` with `user` taken from a link | remove `allow_guest`. Require login. A signed link proves the URL was issued, not who is clicking it |
| A check (IP allow-list, 2FA, enabled user) enforced on interactive login but not on API key, OAuth or `auth_hooks` logins | enforce it at the single point every path passes — `frappe.auth.validate_auth()` — after the user is resolved |
| Reset, one-time-login or invite links built with `frappe.utils.get_url()` | `get_url(uri, allow_header_override=False)` — otherwise the request `Host` header chooses the link's domain, and the token is mailed pointing at the attacker |
| A database error surfacing during authentication | catch it and raise `frappe.AuthenticationError` |
| A secret compared with `==` | `hmac.compare_digest` |
| A signed URL | `frappe.utils.verified_command.get_signed_params` / `verify_request` (HMAC, constant-time compare) |

Done when: every path that authenticates a user reaches the same checks, and no request header or
parameter selects the identity or the link's domain.

### 2. Keys and tokens: random, stored, expiring

A key derived from data — `sha224(creation_timestamp)` — is guessable as soon as any other endpoint
reveals that data. Generate a random key with `frappe.generate_hash(...)` (backed by `secrets`), store
it, look it up instead of recomputing it, and give it an expiry. Keep Password fields server-side:
read one with `frappe.utils.password.get_decrypted_password` at the point of use, and return
something else.

Done when: no key can be computed from data a caller can read, and every key can expire or be revoked.

### 3. Enumeration: one response for every case

"Not found", "disabled", "not allowed", a 404, a `frappe.db.exists` throw before the permission
check, a different timing — each tells the caller whether a record or user exists. Return the same
body and status in every case, and do the work silently only where it applies:

```python
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=get_password_reset_limit, seconds=60 * 60)
def reset_password(user: str) -> str:
	try:
		user_doc = frappe.get_doc("User", user)
		if user_doc.name != "Administrator" and user_doc.enabled:
			user_doc.reset_password(send_email=True)
	except frappe.DoesNotExistError:
		frappe.clear_messages()
	return frappe.msgprint(_("If an account with this email exists, password reset instructions have been sent."))
```

For a guest form that creates a record keyed on a user, a request for an unknown user can return a
fake, unsaved document instead of an error, and the fields that reveal identity are stripped from
`as_dict`.

Done when: status, body, headers and timing are indistinguishable for an existing and a missing
identity.

### 4. Disclosure: messages, logs, and stale access

- **A permission refusal can name the refused record's linked value** to a user fenced by User
  Permissions. For a docname the method looked up itself, refuse with the constant
  `frappe.throw_permission_error()`, as [missing-authorization.md](missing-authorization.md) step 2 says.
- **`frappe.throw` / `msgprint` text built from data the caller cannot read** discloses it. Name
  only what the caller supplied.
- **Tracebacks:** frappe masks local variables named like password, secret, token or key in logged
  tracebacks. Keep secrets in variables named that way, and keep them out of exception messages.
- **A subscription, digest or follow job** must re-check
  `frappe.has_permission(dt, "read", doc=name, user=recipient)` every time it sends, and drop the
  subscription when access is gone. Authorising once, at subscribe time, keeps mailing data after
  revocation. Check field `permlevel` for any changed-field data it includes.

Done when: a refusal, an error and a scheduled email each contain nothing the recipient could not read
directly.

### 5. Verify

- Send each request with `Host: attacker.example`. Open the mailed link — its domain must be the site's.
- For every login path (password, API key, OAuth bearer, `auth_hooks`), confirm the added check fires.
- Compare an existing and a missing identity: status, body, headers, `_server_messages`, timing.
- Trigger a refusal on a record blocked by a User Permission and read `_server_messages`: it must not
  name the linked value.
- Revoke a recipient's access and run the job: nothing is sent, the subscription is gone.
- Start with the known-positive control ([verify.md](../verify.md)):
  each check must fail on the pre-fix code.

Done when, on every release line: every check failed before the fix and passes after it.

## References

- Shipping, backports and the public PR: [the security workflow](../workflow.md).
