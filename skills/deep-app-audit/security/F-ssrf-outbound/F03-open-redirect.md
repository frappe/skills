# F03 — Open redirect

**Scope:** redirect targets from the request.

**Why:** an unsanitised redirect target, including an OAuth `state` value, sends the user to an
attacker site with session context.

## Find
- `rg -n "redirect_to|redirect_location|response\[.location.\]|frappe\.local\.flags\.redirect" --type py`
  plus `next`, `return_to`, `continue`, `callback` parameters.
- Login and logout redirects, OAuth `state` and `redirect_uri`, portal post-action redirects,
  web form success URLs, `frappe.set_route` from a URL parameter on the client.

## Confirm
- Check the validation: a leading-slash check is bypassable with `//evil.com` and
  `/\evil.com`; a substring/prefix host check is bypassable with `evil.com.yoursite.com` or
  `yoursite.com.evil.com`; scheme-relative and `javascript:` targets both matter.
- Chain it: open redirect plus an OAuth flow is token theft, not a Low.

## Report
Give the redirect URL that lands off-site.
