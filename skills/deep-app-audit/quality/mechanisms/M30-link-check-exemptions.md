---
id: M30
---
# M30 — `ignore_links_on_delete` and `auto_cancel_exempted_doctypes`

**What:** Two hooks list doctypes that the link checks skip. A doctype in
`ignore_links_on_delete` does not block a delete when it links to the document being deleted. A
doctype in `auto_cancel_exempted_doctypes` is left alone when a linked document is cancelled,
instead of being cancelled with it.

**Guards:** Both hooks are flat lists that merge across every installed app, so an entry applies
to every site that has the app, not to the app's own flows only. `ignore_links_on_delete` is read
on delete only; on cancel the framework reads the document's `ignore_linked_doctypes` flag
instead. The exemption covers static links and dynamic links, and the check that reports linked
child rows. Skipping the check does not remove the row: the link stays behind and points at a
name that no longer exists.

## Good use

The hooks are for a log-like doctype: a record that the app writes as a trace of something that
happened, that no other record depends on, and that carries no value of its own. A Communication,
a ToDo, an integration request and a version row are of this kind. Deleting the document they
point at must not fail, and a stale reference in them does nothing worse than name a document
that is gone.

```python
ignore_links_on_delete = ["Fleet Sync Log"]
```

A transactional doctype never belongs in either list. Its link is the reason the framework
refuses the delete. An exemption there produces a ledger entry, an invoice line or a stock row
that points at nothing, and the failure surfaces much later, in a report or a reconciliation.

An app whose log doctype grows also needs a way to remove old rows, so the exemption stays a
statement about references and not a licence to keep every row forever.

## Rules

- A35 — `ignore_links_on_delete` and `auto_cancel_exempted_doctypes` are for log-like DocTypes
- B26 — Update every dependent record on rename, cancel and delete
