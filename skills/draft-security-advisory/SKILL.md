---
name: draft-security-advisory
description: Turn a vulnerability report into a publication-ready GitHub Security Advisory.
disable-model-invocation: true
---

# GitHub Security Advisory Writer

Turn the vulnerability report the user provides into a publication-ready GitHub Security Advisory (GHSA): terse text in each of the form's text fields, with the precision carried by GitHub's structured fields.

## Class, not instance

The advisory speaks at the level of the vulnerability **class**: the flaw class (SQL injection, SSTI, missing authorization), the broken or missing control, the feature area, the risk category. Everything at the level of the **instance** — function names, file paths, field names, endpoints, configuration keys, code snippets, payloads — stays out, so a reader can never work backwards from the advisory to the patched code path. A published advisory locates a flaw no more precisely than "certain endpoints in the Stock module", "a configuration field", "a certain page", "names of a few records" — match that register.

The one locator allowed is the **module or feature area**: "the Stock module", "Accounts reports", "the customer portal", "POS". A module holds hundreds of endpoints, so naming it does not lead a reader to the code path, and it is what makes one advisory distinguishable from the next. Never go below it: no screen, form, report name, field, or endpoint.

## Use the app's own terms

Write in the vocabulary of the affected app, as its users and its module list name things, not in a generic paraphrase:

- **Modules** by the name the app gives them, capitalised as the app shows them. For ERPNext: Accounts, Stock, Manufacturing, Buying, Selling, CRM, Support, Projects, Assets, Setup, Regional. Write "the Accounts module", not "the accounting module".
- **Data** by the app's standard term or abbreviation: "BOM", not "bill of materials"; "POS", not "point of sale"; "Sales Invoice", not "a sales bill"; "Purchase Order", not "a buying order". A term the app uses across a whole module locates the data, not the code path.

Read the app's module list and its labels when unsure of a name. The class-not-instance rule still holds: a term names the kind of data, never the one form, report or endpoint that exposed it.

## Distinguishable for CVE assignment

A CVE describes one flaw, and the CNA (the organisation that assigns the CVE) must be able to tell it from every other CVE. Advisories published together with the same title, the same body and the same versions read as one flaw filed several times, and their CVE requests get declined. Every advisory in a batch must therefore differ from its siblings on facts that do not reveal the code:

| Attribute | Example |
|---|---|
| Module or feature area | "in the Stock module", "in the customer portal" |
| What the attacker reaches or changes | "pricing data of other customers", "the status of submitted documents" |
| Minimum privilege | "any authenticated user, including a portal user", "a user with the Accounts User role" |
| Scope crossed | "records of other companies", "records excluded by the caller's user permissions" |
| CWE | the most specific id that fits; CWE-863 for a check that exists but is wrong, CWE-639 for a user-controlled key |

One advisory covers one independently fixable flaw. Do not merge independent flaws into one advisory, because the merged advisory can get only one CVE.

## Title

Pick the established pattern that fits. **Within one batch of advisories, every title must be unique**; a title may repeat one from an earlier batch.

- Injection flaws: `Possibility of {class} in {module or feature area} due to missing validation`
- Authorization flaws: `Unauthorised {action} in {module or feature area} due to missing validation` (British spelling). Make `{action}` name the data or the operation: "access to financial data", "modification of master data".
- Outcome-led: `{Outcome} via {class} in {module or feature area}` — e.g. `Account takeover via reflected XSS in portal pages`
- When two flaws in a batch share a module and an action, make the data more specific until the titles differ. Never add an instance-level identifier to separate them.

## Text fields

GitHub's form has four required text fields, in this order. Every one is published, so the class-not-instance rule binds all four — including Details and Proof of concept, whatever their placeholder text asks for.

Give each field its own job, so the four never repeat each other:

| Field | Contents |
|---|---|
| **Summary** | One line: the flaw class and the module or feature area it sits in ("certain endpoints in the Stock module", "customer portal pages"). |
| **Details** | One or two sentences: the missing or broken control, and what the fix does in general terms ("validation was added"). Leave out the preconditions and the affected releases, because Impact and Affected products already hold them. End with the workaround line: "No workaround available; upgrading is required." Amend it only when a real workaround exists. |
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

Then compare the advisory with every other advisory in the same batch, and with any advisory already published for the same release. No two may share a title, and no two may share a Summary or Impact field. If two read alike, add the module, the data reached, the privilege or the scope that separates them.
