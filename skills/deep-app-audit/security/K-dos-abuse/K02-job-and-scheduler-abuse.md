# K02 — Background job and scheduler abuse

**Scope:** the queue as an attack surface.

## Find
- `rg -n "frappe\.enqueue|enqueue_doc|frappe\.call\(" --type py` — for each, is `method`
  or the target document controlled by the request? Cross-reference `B09`.
- Endpoints that enqueue work with no rate limit — queue flooding starves the whole site,
  including other tenants on shared workers.
- Job arguments carrying credentials or PII into the queue backend, and who can read the
  queue (Redis access, `RQ Job` doctype permissions).
- `Scheduled Job Type` and `Server Script` (scheduler type): who can create or modify one,
  and what identity it runs as.
- Jobs that run as Administrator on data supplied by a low-privilege user.

## Confirm
- The severity hinges on the identity the job runs as. State it.

## Report
Job entry point, controlled parameter, executing identity.
