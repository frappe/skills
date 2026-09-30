---
id: P01
---
# P01 — Endpoint hardening coverage

**Kind:** posture check. It reports coverage over the whole endpoint surface. It does not hunt
for one bug, and it is not verified against the live site.

**Why:** runtime type checking and a role-check decorator each resolve a whole class of issue at
once. Type annotations are the structural fix for `B02`; a role-check decorator is the
structural fix for `A01`. A coverage number tells the maintainer how far that fix has spread.

## Task
1. Enumerate every `@frappe.whitelist()` function and every doctype controller method reachable
   over HTTP. Reuse the entry-point inventory if one was built.
2. **Type annotations.** For each parameter, record whether it has an annotation, and whether
   the annotation is specific enough to constrain the input (`str` constrains; `Any`, untyped,
   and bare `dict` do not). Flag parameters that are annotated but then used in a way the
   annotation does not cover (annotated `str`, passed to `get_all(filters=...)`).
3. **Role checks.** Classify each endpoint: (a) explicit role or permission check present,
   (b) delegates to a call that checks (`get_doc().save()`), (c) no check at all.
4. For class (c), record the sinks it reaches: `db.sql`, `db.set_value`, `get_doc`, file IO,
   `sendmail`, `enqueue`.

## Output
- Annotation coverage as a percentage, plus the unannotated parameters ranked by how dangerous
  the sink they reach is.
- The three role-check counts, plus the ranked class-(c) worklist.
- Any pattern where a whole module is unguarded — that usually means one shared helper needs
  the check, not fifty call sites.
- A suggested enforcement step: an opt-in hook flag first, then default-on, then in the new-app
  boilerplate.

Once coverage is high this runs as a PR gate: a new whitelisted method without annotations
fails.
