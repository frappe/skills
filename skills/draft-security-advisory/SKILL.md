---
name: draft-security-advisory
description: Turn a vulnerability report into a publication-ready GitHub Security Advisory.
disable-model-invocation: true
---

# GitHub Security Advisory Writer

Turn the vulnerability report the user provides into a publication-ready GitHub Security Advisory (GHSA): a terse two-section body, with the precision carried by GitHub's structured form fields.

## Class, not instance

The advisory speaks at the level of the vulnerability **class**: the flaw class (SQL injection, SSTI, missing authorization), the broken or missing control, the feature area, the risk category. Everything at the level of the **instance** — function names, file paths, field names, endpoints, configuration keys, code snippets, payloads — stays out, so a reader can never work backwards from the advisory to the patched code path. A published advisory locates a flaw no more precisely than "certain endpoints", "a configuration field", "a certain page", "names of a few records" — match that register.

## Title

Pick the established pattern that fits; when an earlier advisory for the same project covered the same class, reuse its title verbatim — repeated titles are house style, not a defect:

- Injection flaws: `Possibility of {class} due to missing validation`
- Authorization flaws: `Unauthorised {action} due to missing validation` (British spelling)
- Outcome-led: `{Outcome} via {class}` — e.g. `Account takeover via Reflected XSS`
- Feature-scoped: `{Class} in {feature area}` — a last resort, only when none of the patterns above fit; never to make a title unique, since identical titles across advisories are fine. Generalize the feature area so the exact feature stays unrevealed: name an umbrella surface one level broader than where the flaw sits (e.g. "portal pages", not the specific portal), never a module, screen, or record type.

## Advisory body

Exactly two sections:

```markdown
### Impact
{One or two sentences: where the flaw sits, at class level; what control
was missing; what the attacker gains and the minimum privilege needed.}

### Workarounds
No workaround available; upgrading is required.
```

Reuse the stock Impact sentence when the class has one:

- SQL injection: "Some endpoints were vulnerable to SQL injection through specially crafted requests, which would allow a malicious actor to extract sensitive information."
- Missing authorization: "Certain endpoints failed to enforce proper authorization checks, allowing users to modify data beyond their permitted role."

For other classes, write the sentence in the same register: "{Class} through {vague vector} allows {an authenticated user / a malicious user} to {capability}." Amend the Workarounds line only when a real workaround exists.

## Form fields

After the body, list the values for GitHub's advisory form:

- **Ecosystem / package:** the project's ecosystem and package name
- **Affected / patched versions:** one row per currently supported release stream — ask the user which streams are supported if not stated in the report; affected `< {first fixed release}`, patched `{first fixed release}`
- **CVSS:** v3.1 vector and score, derived from the rules below, with a one-sentence rationale for each non-obvious metric choice (PR, S, C, I)
- **Severity:** the band the score falls in
- **CWE:** the most specific id available
- **Credits:** reporter(s) from the report as *reporter*; whoever authored the fix as *remediation developer*

That is the whole advisory: the body carries no summary, no root-cause walkthrough, and no proof of concept, and the CVE field stays empty — GitHub assigns one after publication. The report's PoC informs the CVSS metrics only.

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

**Severity bands** from the CVSS base score: 9.0–10.0 Critical · 7.0–8.9 High · 4.0–6.9 Medium · 0.1–3.9 Low.

If the report supplies its own CVSS or CWE, validate it; where your analysis disagrees, use your analysis and note the discrepancy in one sentence.

## Final check

The advisory is complete when the body is exactly Impact + Workarounds, every form field above has a value, the CVSS score falls in the stated severity band, and a re-read of the title and Impact finds zero instance-level identifiers.
