---
name: draft-security-advisory
description: Turn a vulnerability report into a publication-ready GitHub Security Advisory.
disable-model-invocation: true
---

# GitHub Security Advisory Writer

Turn the vulnerability report the user provides into a complete, publication-ready GitHub Security Advisory (GHSA).

## Class, not instance

The advisory speaks at the level of the vulnerability **class**: the flaw class (SSTI, SQL injection, IDOR), the broken or missing control, the product or high-level feature area, the risk category. Everything at the level of the **instance** — function names, file paths, field names, endpoints, configuration keys, code snippets, copy-paste payloads — stays out, so a reader can never work backwards from the advisory to the patched code path. This rule binds the title and every section below.

## Output format

First output:

**Suggested title:** `{Vulnerability class} in {product or component} allows {attacker gain, 5 words or fewer}`

The closing phrase names what the attacker gains ("allows unauthorized data disclosure"), never what was broken or fixed. Example: `Server-Side Template Injection in ERPNext allows unauthorized data disclosure`.

Then the advisory as a single markdown document:

---

## [GHSA-XXXX-XXXX-XXXX] — {same title}

**Package:** {ecosystem}/{package-name}
**Affected versions:** {range, e.g. `>= 14.0.0, < 14.62.4`}
**Patched versions:** {version, or "Not yet patched"}
**Severity:** {from the severity bands below}

### Summary

One or two sentences for a developer scanning their dependency feed: the vulnerability class and the minimum privilege level required to exploit it.

### Vulnerability details

3–6 sentences at the mechanism level: what kind of input is accepted, how it reaches the vulnerable operation, and which safety control is absent or broken.

### Impact

One to three sentences naming the risk category — "unauthorized data disclosure", "privilege escalation". Bound what is NOT achievable when that significantly changes the risk profile.

### CVSS

**Vector:** `CVSS:3.1/AV:?/AC:?/PR:?/UI:?/S:?/C:?/I:?/A:?`
**Score:** X.X (Severity)

One-sentence rationale for each non-obvious metric choice (PR, S, C, I).

### CWE

**Primary:** CWE-XXXX — {name}
**Secondary (if applicable):** CWE-XXXX — {name}

One sentence on why the primary CWE applies.

### Proof of concept

Plain-text reproduction steps. Describe payloads and any PoC videos or write-ups in prose rather than reproducing them, so nothing is copy-paste runnable against a live system.

---

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

**Severity bands** from the CVSS base score: 9.0–10.0 Critical · 7.0–8.9 High · 4.0–6.9 Medium · 0.1–3.9 Low.

If the report supplies its own CVSS or CWE, validate it; where your analysis disagrees, use your analysis and note the discrepancy in one sentence. CVE IDs are the CNA's to assign — the advisory carries none.

## Final check

The advisory is complete when every section above is present, the CVSS score falls in the stated severity band, and a re-read of the title, Summary, Vulnerability details, and Impact finds zero instance-level identifiers.
