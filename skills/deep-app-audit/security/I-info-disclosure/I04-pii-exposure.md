---
id: I04
area: info-disclosure
---
# I04 — PII exposure

**Scope:** personal data reachable beyond its intended audience.

**Why:** salary, patient, and employee contact data are the highest-impact reads on a typical site.

## Find
- Enumerate the doctypes holding PII in this app: User, Contact, Employee, Patient, Student,
  Lead, Customer, Salary Slip, Address, and any app-specific equivalent.
- For each, find every read path: direct API, helper endpoints, search, reports, dashboards,
  notifications, exports, print formats, socketio payloads.
- User listing endpoints returning email, phone, full name, or avatar to peers or to Website
  Users.
- Salary, health, and identity-document fields — check `permlevel` and encryption.
- Derived artefacts: activity logs, energy points, mention lists, "who viewed" trackers.

## Confirm
- Name the specific fields and roughly how many records are reachable. Volume changes severity.

## Report
Flag anything regulated (health, payroll, identity documents) explicitly.
