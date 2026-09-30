---
id: M09
---
# M09 — Session hooks

**What:** `LoginManager` fires four events through `run_trigger`: `before_login` at the start of
a password login, `on_login` after authentication succeeds, `on_session_creation` when a new
session is made, and `on_logout` before the session is deleted. An app uses them to seed session
defaults, to choose a landing page, and to clean up on logout.

**Guards:** `run_trigger` calls every handler for the event with `login_manager=self`, through
`frappe.call`. `on_session_creation` runs only when the session is new, not when an existing
session resumes. `before_login` runs before the password is checked, so no user is known yet. An
exception in any handler propagates and stops the login or the logout.

## Good use

Declare the handler with the argument the call site passes, and read the user from the login
manager.

```python
# my_app/session.py
import frappe


def on_session_creation(login_manager):
    frappe.local.response["home_page"] = _home_page_for(login_manager.user)
```

Use `on_session_creation` for anything that must happen once per session, such as setting a
redirect or writing a session default. Use `on_login` for work that must happen on every
successful authentication.

Use `on_logout` to release what the app holds for that session. Read
`frappe.session.user` before the session is gone.

Raise only when blocking the login is the intent, and say why in the message. Any other failure
must be caught and logged. A telemetry call or an external sync that raises in `on_login` locks
every user out of the site.

Keep the handlers short. Login is interactive and the user waits for it, so a slow query or a
network call in `on_login` is felt directly.

Do not put a permission decision here. These hooks shape the session; they do not decide what
the user may read.

## Rules

- A25 — A hook handler accepts every argument the call site passes
- B40 — An optional step must not fail the main flow, and a swallowed failure must be logged
