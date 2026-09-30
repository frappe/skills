# G01 — Secret storage

**Scope:** where credentials live.

**Why:** never store a secret in plaintext. Always use the `Password` fieldtype.

## Find
- DocFields holding secrets that are *not* `fieldtype: Password`: grep field names for
  `password`, `secret`, `token`, `key`, `api_`, `private`, `credential`, `passphrase` across
  every `*.json` and check the fieldtype.
- Secrets written to `site_config.json`, `common_site_config.json`, fixtures, or a `Data`
  field.
- `get_decrypted_password` call sites — is the decrypted value returned to the client or put
  in a template context?
- Encryption key handling: is it retrievable through any endpoint or template global?
- Backup encryption: is the key stored next to the backups it protects, and does it travel with
  them? Who can download a backup — cross-reference `E04` for the serving route.
- Data at rest: database encryption, and TLS private key file permissions.
- Hardcoded secrets in the repo — run a secret scan over the full history, not just HEAD.

## Confirm
- A `Password` field is still readable by anyone who can call `get_decrypted_password`
  indirectly. Check the callers too.
- Some of this belongs to the deployment, not the app. Keep app-level findings here and mark
  deployment-level ones so they route to the right team.

## Report
Field, doctype, storage form, who can read it.
