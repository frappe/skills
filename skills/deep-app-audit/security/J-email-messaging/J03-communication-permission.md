# J03 — Communication and comment permission

**Scope:** the `Communication`, `Comment`, and `Notification Log` doctypes.

**Why:** the Communication permission hooks decide who reads every thread, and comment
authorship taken from the request is spoofable.

## Find
- The `has_permission` and `permission_query_conditions` hooks for `Communication` — read the
  function body; a hook that returns nothing restricts nothing.
- Read/write access to a Communication whose `reference_doctype`/`reference_name` the caller
  cannot read.
- Mutation endpoints: read-state, `seen`, mailbox flags, `_liked_by`, split/merge operations
  on a thread.
- Comment creation with a client-supplied author, and unauthenticated Lead/Communication
  creation.
- Whether comment content is sanitised before Desk rendering — cross-reference `C01`.

## Confirm
- Reading a thread usually leaks more than reading the document it hangs off. Weigh it that way.

## Report
Name the hook and what it fails to constrain.
