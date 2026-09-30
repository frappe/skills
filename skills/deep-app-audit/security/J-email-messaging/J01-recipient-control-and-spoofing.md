---
id: J01
area: email-messaging
---
# J01 — Recipient control and outbound spoofing

**Scope:** who the app will send a message to, on whose behalf.

**Why:** a recipient list taken from the request lets any user send mail or SMS as the company.

## Find
- Whitelisted methods reaching `frappe.sendmail`, `send_sms`, notification dispatch, or
  `Email Queue` insertion. For each: who can call it, and can the caller set `recipients`,
  `sender`, `subject`, `message`, `template`, or `attachments`?
- `sender` / `reply_to` taken from the request — that is outbound spoofing using the org's
  reputation and SPF alignment.
- Attachment selection by `print_format` and document name — can the caller attach a document
  they cannot read?
- Guest-reachable send paths (OTP, contact forms, share-by-email) — also an `A04` case.

## Confirm
- Free outbound email or SMS from a company domain is High even without data disclosure.

## Report
State: who sends, as whom, to whom, with what content.
