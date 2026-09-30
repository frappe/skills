# L01 — Python dependency CVEs

**Scope:** `pyproject.toml`, `requirements*.txt`, and the resolved environment.

**Why:** unpatched python dependencies, with no CVE tracking behind them.

## Find
- Parse the declared dependencies and the resolved versions (`uv pip list`, `pip freeze` in
  the bench env — resolved beats declared).
- Cross-check against a vulnerability database (`pip-audit`, `uv pip audit`, `osv-scanner`).
- Note transitive dependencies separately from direct ones; the fix differs.
- Check for dependencies that are unmaintained, yanked, or renamed.

## Confirm
- For each CVE, determine whether the vulnerable code path is reachable from this app. An
  unreachable CVE in a transitive dep is a patch-hygiene item, not an incident.
- Note where the fixed version requires a major upgrade — that is a planning input.

## Report
Package, installed version, CVE, fixed version, reachable yes/no. Sort by reachable-and-severe.
