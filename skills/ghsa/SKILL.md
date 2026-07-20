---
name: ghsa
description: Write a complete, publication-ready GitHub Security Advisory (GHSA) from a vulnerability report. Use when the user provides a vulnerability report or asks to draft/write a security advisory, GHSA, or CVE-style writeup — producing the title, summary, vulnerability details, impact, CVSS vector and score, CWE, and proof of concept. Deliberately withholds details (functions, files, fields) that would reveal the patched code path.
---

# GitHub Security Advisory Writer

When the user provides a vulnerability report, produce a complete, publication-ready GitHub Security Advisory (GHSA).

## Output format

Before the advisory, output a short block:

**Suggested title:** {title — see Title rule below}

Then produce the advisory as a single markdown document structured exactly as below.

---

## [GHSA-XXXX-XXXX-XXXX] — {same title as suggested above}

**Package:** {ecosystem}/{package-name}
**Affected versions:** {version range, e.g. `< 15.x.x` or `>= 14.0.0, < 14.62.4`}
**Patched versions:** {patched version or "Not yet patched"}
**Severity:** {Critical / High / Medium / Low}

### Summary

One or two sentences maximum. Name the vulnerability class and the minimum privilege level required to exploit it. Do not describe the root cause mechanically or reference specific functions, files, or data types. Write for a developer scanning their dependency feed.

### Vulnerability details

Describe the root cause precisely: what input is accepted, how it flows to the sink, and what safety control is absent or broken. Reference the relevant file path and function name. Include a short code snippet only if it materially aids understanding. This section should be 3–6 sentences.

### Impact

One to three sentences. Describe the risk category only — e.g., "unauthorized data disclosure" or "privilege escalation." Do not enumerate specific tables, APIs, data classes, or step-by-step attacker capabilities. Bound what is NOT achievable if that significantly changes the risk profile.

### CVSS

**Vector:** `CVSS:3.1/AV:?/AC:?/PR:?/UI:?/S:?/C:?/I:?/A:?`
**Score:** X.X (Severity)

Provide a one-sentence rationale for each non-obvious metric choice (PR, S, C, I).

### CWE

**Primary:** CWE-XXXX — {CWE name}
**Secondary (if applicable):** CWE-XXXX — {CWE name}

One sentence explaining why this CWE applies.

### Proof of concept

Describe the reproduction steps in plain text. Do not include working exploit payloads that could be directly copy-pasted to attack live systems. Reference any PoC videos or write-ups by description only.

---

## Analysis rules

**Title:** Format as `{Vulnerability class} in {product/component name} allows {impact in 5 words or fewer}`.

Rules:
- Name only the vulnerability class (e.g., SSTI, SQL Injection, IDOR) and the product or high-level feature area — never a specific function name, file path, field name, or configuration key.
- The impact phrase must describe what the attacker gains, not what was broken or fixed (e.g., "allows data disclosure", not "due to missing input validation").
- A reader should not be able to infer which code path was changed or what the patch touches.
- Example: `Server-Side Template Injection in ERPNext allows unauthorized data disclosure`.

**CVSS metrics** — derive from the report:
- AV: Network if reachable via web UI; Local if shell access required.
- AC: Low unless the report describes a race condition, specific non-default setup, or hard-to-meet precondition.
- PR: None if unauthenticated; Low if any authenticated user or a common operational role; High if admin/superuser only.
- UI: None unless a victim must take an action.
- S: Changed if the exploit reaches resources outside the attacker's own authorization scope (cross-tenant data, other document types the role cannot normally access).
- C: High if the attacker can read arbitrary sensitive records; Medium if limited; None if no confidentiality impact.
- I: High if arbitrary writes or deletes; Low if write is constrained or incidental; None if read-only.
- A: High if service disruption is possible; None if not described.

**CWE selection:** Use the most specific CWE available.
- Template injection → CWE-1336
- SQL injection → CWE-89
- Missing authorization → CWE-862
- Improper input validation → CWE-20
- Code injection (generic) → CWE-94

**Severity label** from CVSS base score:
- 9.0–10.0 → Critical
- 7.0–8.9 → High
- 4.0–6.9 → Medium
- 0.1–3.9 → Low

If the report already provides a CWE or CVSS, validate it. If it disagrees with your analysis, use your analysis and note the discrepancy briefly.

Do not speculate about or assign a CVE ID.
