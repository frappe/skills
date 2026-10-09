---
name: draft-security-advisory
description: Turn a vulnerability report into a publication-ready GitHub Security Advisory.
disable-model-invocation: true
---

# GitHub Security Advisory Writer

Turn the vulnerability report the user provides into a publication-ready GitHub Security Advisory (GHSA): terse text in each of the form's text fields, with the precision carried by GitHub's structured fields.

## Class, not instance

The advisory speaks at the level of the vulnerability **class**: the flaw class (SQL injection, SSTI, missing authorization), the broken or missing control, the feature area, the risk category. Everything at the level of the **instance** — function names, file paths, field names, endpoints, configuration keys, code snippets, payloads — stays out, so a reader can never work backwards from the advisory to the patched code path. A published advisory locates a flaw no more precisely than "certain endpoints", "a configuration field", "a certain page", "names of a few records" — match that register.

## Title

Pick the established pattern that fits; when an earlier advisory for the same project covered the same class, reuse its title verbatim — repeated titles are house style, not a defect:

- Injection flaws: `Possibility of {class} due to missing validation`
- Authorization flaws: `Unauthorised {action} due to missing validation` (British spelling)
- Outcome-led: `{Outcome} via {class}` — e.g. `Account takeover via Reflected XSS`
- Feature-scoped: `{Class} in {feature area}` — a last resort, only when none of the patterns above fit; never to make a title unique, since identical titles across advisories are fine. Generalize the feature area so the exact feature stays unrevealed: name an umbrella surface one level broader than where the flaw sits (e.g. "portal pages", not the specific portal), never a module, screen, or record type.

## Text fields

GitHub's form has four required text fields, in this order. Every one is published, so the class-not-instance rule binds all four — including Details and Proof of concept, whatever their placeholder text asks for.

Give each field its own job, so the four never repeat each other:

| Field | Contents |
|---|---|
| **Summary** | One line: the flaw class and the umbrella surface it sits in ("portal pages", "certain endpoints"). |
| **Details** | Two to four sentences: the missing or broken control, the preconditions (authenticated or not, kind of role), what the fix does in general terms ("validation was added"), and which release lines are affected. End with the workaround line: "No workaround available; upgrading is required." Amend it only when a real workaround exists. |
| **Proof of concept** | The attack shape in general terms, e.g. "An authenticated user with a low-privilege role sends a crafted request to an affected endpoint." No payload, endpoint name, or field name. |
| **Impact** | What the attacker gains, who is exposed, and the minimum privilege needed. |

Reuse the stock sentence when the class has one, splitting it across Summary and Impact:

- SQL injection: "Some endpoints were vulnerable to SQL injection through specially crafted requests, which would allow a malicious actor to extract sensitive information."
- Missing authorization: "Certain endpoints failed to enforce proper authorization checks, allowing users to modify data beyond their permitted role."

For other classes, write in the same register: "{Class} through {vague vector} allows {an authenticated user / a malicious user} to {capability}."

## Structured fields

After the text fields, list the values for the rest of the form:

- **CVE identifier:** leave on "Request CVE ID later" — GitHub assigns one after the draft is created
- **Affected products:** one row per currently supported release stream — ask the user which streams are supported if not stated in the report. Each row: ecosystem, package name, affected `< {first fixed release}`, patched `{first fixed release}`
- **Severity:** CVSS v3.1 vector and score, derived from the rules below, with a one-sentence rationale for each non-obvious metric choice (PR, S, C, I); then the severity the score falls in, named as the form's dropdown names it
- **CWE:** the most specific id available
- **Credits:** reporter(s) from the report as *reporter*; whoever authored the fix as *remediation developer*

That is the whole advisory: no root-cause walkthrough, no payload, no step-by-step reproduction. The report's PoC informs the Proof of concept field's attack shape and the CVSS metrics, nothing more.

## Derivation rules

**CVSS metrics**, from the report:

- AV — Network if reachable via web UI; Local if shell access is required.
- AC — Low, unless the report describes a race condition, non-default setup, or hard-to-meet precondition.
- PR — None if unauthenticated; Low for any authenticated user or common operational role; High for admin/superuser only.
- UI — None, unless a victim must take an action.
- S — Changed when the exploit reaches resources outside the attacker's own authorization scope (cross-tenant data, document types the role cannot normally access).
- C — High if arbitrary sensitive records are readable; Medium if limited; None otherwise.
- I — High for arbitrary writes or deletes; Low for constrained or incidental writes; None if read-only.
- A — High if service disruption is possible; None otherwise.

**CWE** — the most specific available:

- Template injection → CWE-1336
- SQL injection → CWE-89
- Missing authorization → CWE-862
- Improper input validation → CWE-20
- Code injection (generic) → CWE-94
- Path traversal → CWE-22
- XSS → CWE-79
- SSRF → CWE-918
- XXE → CWE-611

**Severity bands** from the CVSS base score: 9.0–10.0 Critical · 7.0–8.9 High · 4.0–6.9 Moderate · 0.1–3.9 Low.

If the report supplies its own CVSS or CWE, validate it; where your analysis disagrees, use your analysis and note the discrepancy in one sentence.

## Final check

Re-read the title and all four text fields. They must hold zero instance-level identifiers.
