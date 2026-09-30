# G03 — Weak randomness and secret generation

**Scope:** how security-relevant values are generated.

**Why:** a predictable token turns an invite or reset link into a permanent passwordless login.

## Find
- `rg -n "import random|random\.|uuid1|time\.time\(\)|frappe\.generate_hash|hashlib\." --type py`
  — flag `random.*` and `uuid1` in any security context.
- `frappe.generate_hash` call sites: check the requested length. Short values used as
  invitation keys, reset tokens, or API secrets are the finding.
- Values derived from predictable inputs: timestamp, autoincrement, username, `md5(name)`.
- Invite and share links: entropy, expiry, revocation.

## Confirm
- State the search space. "128 bits from `secrets`" is fine; "8 hex chars from `random`" is not.

## Report
Include the entropy estimate.
