# K01 — Resource exhaustion

**Scope:** single requests that consume disproportionate resources.

**Why:** endpoints that zip, export, or render unbounded input exhaust memory and disk. OWASP
API4.

## Find
- `limit_page_length` handling: is `0` or a huge value accepted on `get_list` and the REST API?
- Report and Prepared Report generation with no row cap; exports of unbounded size.
- PDF rendering, image resizing, and thumbnail generation on attacker-supplied input
  (decompression bombs, huge dimensions).
- Zip creation and extraction (`zip_files`, backup download, SCORM import) — zip bombs and
  unbounded member counts.
- Regexes applied to user input — check for catastrophic backtracking in validation patterns.
- Recursive structures: nested child tables, deeply nested JSON filters, tree doctype
  traversal with a cycle.
- XML parsing — entity expansion (billion laughs) and external entities.
- Log volume under attacker control: an unauthenticated endpoint that writes an `Error Log`,
  `Access Log`, or `Activity Log` row per call fills the disk. When rotation or retention evicts
  old rows under that load, it also destroys the record of the attack.

## Confirm
- Give a rough resource cost. "Unbounded" needs one concrete number to be actionable.

## Report
Moderate unless it is trivially reachable by Guest.
