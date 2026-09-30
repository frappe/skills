---
id: H05
area: business-logic
---
# H05 — Multi-tenancy, company, and team scoping

**Scope:** shared helpers that forget which tenant they are serving.

**Why:** company and tenant scoping is the only boundary on a shared site. A missing filter
crosses it.

## Find
- Parameters named `company`, `team`, `organization`, `branch`, `department`, `cost_center`,
  `warehouse`, or any other tenant key — is the value validated against what the caller
  may access, or just used?
- Permission decorators that resolve the tenant from the request rather than the session.
- Role guards that read a cached or stale membership — test the case of a newly created user
  that has no cached value yet.
- Aggregation endpoints (dashboards, notification counts, search) that omit the tenant filter.
- Resource transfer / ownership change endpoints.

## Confirm
- Verify with a second tenant in mind: what does user-of-tenant-A see of tenant-B?

## Report
High by default; Critical when it crosses paying-customer boundaries.
