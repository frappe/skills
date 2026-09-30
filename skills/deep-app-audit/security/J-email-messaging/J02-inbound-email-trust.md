# J02 — Inbound email trust

**Scope:** what the app believes about mail it receives.

**Why:** inbound mail is attacker-controlled input. A forged `From:` header can make the app
treat the sender as a System User, and imported mail can be visible to every user.

## Find
- Inbound parsing: `Email Account` pull, `frappe.email.receive`, the sender-to-User matching
  logic. How is the sender identified — raw `From:` header, envelope sender, or a verified
  value? Are encoded-words, display names, comments, and multiple addresses handled?
- What privileges follow from being recognised as a User: comment authorship, ticket creation,
  document updates by email, `reply_to_email` command handling.
- Whether SPF/DKIM/DMARC results are consulted at all before trusting a sender.
- Where imported mail lands and who can read it — `Communication` permission and inbox scoping.
- HTML email bodies rendered later — cross-reference `C04`.

## Confirm
- Show the header that produces the misidentification.

## Report
High when an unauthenticated sender gains an authenticated identity.
