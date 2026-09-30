---
id: M29
---
# M29 — Notification, Webhook, Assignment Rule and Auto Repeat

**What:** These doctypes let a user react to a document event from the desk, with no code.
`run_method` calls them after the controller method and after the `doc_events` handlers: first
the Notifications for the doctype, then the Webhooks, then the DocType Event Server Scripts.

**Guards:** Each consumer is muted by a different set of flags. A Notification is skipped for
`onload`, during a patch, during an install, and during an import that mutes emails. A Webhook is
skipped during an import, a patch, an install and a migrate, and it is queued on
`frappe.local` and sent when the transaction commits. A DocType Event Server Script is skipped
during an install and a migrate. A Notification whose module is disabled is left out. A Webhook
condition is evaluated with `safe_eval` against the document. A Webhook for `on_change` or
`before_update_after_submit` does not fire on insert.

## Good use

These records belong to the site. They express what one site wants to happen around a document,
and an administrator can read them in a list and switch them off.

A Webhook is the right way to tell an external system about a document, because it is queued and
flushed after the commit. The receiver never sees a document that a later rollback removed, and
a slow receiver does not slow the save.

A Notification carries the site's message text and its recipients, which change more often than
code does.

App code cannot depend on any of them. An app that must send a message or call a service writes
that call in its own controller or `doc_events` handler, and enqueues it after the commit.
Install code, patches and migrate code cannot use them at all: the flags mute every consumer,
so a patch that creates documents produces no notification, no webhook and no server script run.

A data migration that must produce these effects triggers them itself, after the patch, from a
job that runs with the flags clear.

## Rules

- A23 — Install, migrate, and patch code cannot rely on Notifications, Webhooks, or Server Scripts
- B04 — Enqueue a job after commit when it reads what the request wrote
- B40 — An optional step must not fail the main flow, and a swallowed failure must be logged
