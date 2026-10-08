# The branch ledger

One column per confirmed release line, one row per piece of evidence. Every cell holds evidence (a
sha, a verdict, a site name, a link) or `n/a — <reason>`. The fix is done when no cell is empty.

The columns come from `scripts/release_lines.sh`, confirmed by the human. An app that ships from
`main` alone has one column. An app with `develop` and two hotfix lines has three.

| | `<line 1>` | `<line 2>` | `<line 3>` |
| --- | --- | --- | --- |
| bench | `<path>` | | |
| frappe branch | `<branch>` | | |
| base head at pre-flight | `<sha>` | | |
| flaw at head | vulnerable / fixed by `<sha>` | | |
| fix shape | written / cherry-picked from `<sha>` / n/a | | |
| frappe APIs read at the line's frappe | `<api>`: ok, `<api>`: line's equivalent used | | |
| known-positive control | payload worked before the fix | | |
| fix differential | `FIXED`, control ok | | |
| class payloads, before → after | worked → refused | | |
| other half | authorization: guarded | | |
| sibling sweep | `<n>` instances, all fixed | | |
| two-site regression: fresh site | `<site>` at `<sha>`: pass | | |
| two-site regression: pre-patch site + migrate | `<site>`: patch in Patch Log, pass | | |
| review | no findings / `<n>` fixed | | |
| differences from other lines | none / `<reason>` | | |
| pull request | `<link>` | | |
| merged sha | `<sha>` | | |
| first fixed release | `vX.Y.Z` / unreleased | | |

The ledger describes the flaw, so it lives in the private record and stays out of every public
pull request.
