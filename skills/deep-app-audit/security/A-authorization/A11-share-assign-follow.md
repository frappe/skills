---
id: A11
area: authorization
---
# A11 — Sharing, assignment, follow, and notification side-channels

**Scope:** the cross-user features that quietly widen access.

**Why:** share, assign, and follow write permission records. They are permission grants behind a
collaboration UI.

## Find
- `frappe.share.add` / `add_docshare` call sites — is `share` permission required of the
  caller?
- `assign_to.add` — can a user assign a document they cannot read, or assign to a user to
  create a notification containing document content?
- Document Follow: can a user follow a document they cannot read, and does the digest email
  then deliver its content?
- Energy Point Log, Activity Log, Notification Log, ToDo, Comment: are these readable
  cross-user? They embed titles and field values from documents.
- Unfollow/unshare endpoints operating on someone else's row.

## Confirm
- The leak is usually in the derived artefact (notification text, digest email), not the
  primary doctype.

## Report
Name the artefact that carries the leaked content.
