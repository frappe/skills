---
id: M49
---
# M49 — Email and SMS

**What:** An app changes outgoing mail and SMS through a small set of hooks.
`make_email_body_message` receives the built message and may edit the MIME root. `email_css`
adds stylesheets that are inlined into every HTML mail. `default_mail_footer` adds a line to
the standard footer. `welcome_email` returns the subject of the welcome mail. `send_sms`
replaces the SMS transport. `send_token_via_sms` replaces the transport for the two-factor
token. `notification_skip_email_types` and `notification_self_notify_types` change which
notification logs also send mail.

**Guards:** The hooks split into two groups. `make_email_body_message`, `email_css`,
`default_mail_footer`, `notification_skip_email_types` and `notification_self_notify_types`
accumulate: every app's value is used. `welcome_email`, `send_sms` and `send_token_via_sms`
read `[-1]`, so only the last app on the bench answers and the others are silently dropped.
`email_css` paths are resolved as bundled assets and a path that does not exist on disk is
skipped with no message. Mail is sent from a background worker, so a handler that raises fails
the queue entry, not the request that asked for the mail.

## Good use

An app that owns the SMS transport declares one handler with the signature of the function it
replaces.

```python
# hooks.py
send_sms = "my_app.sms.send"
```

```python
# my_app/sms.py
def send(receiver_list, msg, sender_name="", success_msg=True):
	...
```

The replacement is total. A second app on the same bench that also declares `send_sms` loses
its handler with no warning, so an app declares it only when the site is meant to route all SMS
through it.

An app that adds a line to the mail footer uses `default_mail_footer`, which merges. Each app's
line is rendered on its own row, so no app has to know what the others added.

```python
# hooks.py
default_mail_footer = "<div>Sent by My App</div>"
```

A `make_email_body_message` handler edits the message it is given and returns nothing. It runs
for every outgoing mail on the site, including password resets and notifications, so it stays
cheap and it does not raise on a message it does not recognise.

Every mail template is rendered against documents the author did not choose. The template
guards missing values, and the strings a user reads are translatable.

## Rules

- A27 — A handler for a last-wins hook must yield to the apps it does not own.
- B42 — A template must render when a value is missing.
- B40 — An optional step must not fail the main flow, and a swallowed failure must be logged.
