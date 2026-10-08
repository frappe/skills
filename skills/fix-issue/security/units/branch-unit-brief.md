# Brief for one branch unit

Fill this in once per release line and give it to that line's agent, working in that line's bench.
Each agent sees only its own line. The coordinating agent holds the branch ledger.

The unit agent reads the references from where `fix-issue` is installed, so give it absolute paths:
`<fix-issue>/security/...`.

```markdown
## Fix: <one line, in plain change language>

**Release line:** <line>   **Bench:** <path>   **App:** <app>   **Frappe:** <branch, from frappe-dependencies>
**Fix branch:** <fix/...>   **Remote:** <upstream>

### The flaw
- Locations: <file::function>, <file::function>
- Actor and request: <actor> sends <method> <path> with <payload>
- Class reference: <fix-issue>/security/classes/<class>.md
- Also check the other half: <fix-issue>/security/classes/missing-authorization.md
- Siblings on this line: <list from the sweep>, or "run the sweep again on this line"
- Already fixed on: <line: sha> (probe with `git cherry-pick -n`), or "no line yet"

### Steps
1. Pre-flight: `<fix-issue>/security/scripts/preflight.sh <bench>/apps/<app> <line> <fix-branch>`.
   Run the known-positive control at the new head. When the line is already fixed, stop and report
   the sha.
2. Port or write the fix with the class reference, against this line's frappe: read every frappe
   API the fix calls at <frappe branch>, as <fix-issue>/security/frappe-versions.md says. Keep names
   and shapes the same as on <reference line> wherever this line's frappe allows. Report each
   difference with its reason.
3. Verify with <fix-issue>/security/verify.md: the class payloads before and after, the fix
   differential with its control, and the two-site regression.
4. Review in a separate agent, as `fix-issue` step 5 says. Act on the findings, then verify again.
5. Commit with a plain `fix(<module>): ...` subject and open the pull request against <line> with
   an empty description. Push after the human approves.

### Report back: one ledger column
base head · flaw at head · fix shape · control · differential verdict · payloads before → after ·
other half · siblings · fresh-site result · pre-patch-site result (patch in Patch Log) · review ·
differences · pull request link
```

## What every unit keeps to

- Cut the fix branch from the remote head after a fresh fetch, from a bench with no work in progress.
- Before writing a helper whose body is a permission check, a refusal or a path check, search
  `apps/frappe` on this line. Frappe usually has it, and it can behave differently on this major.
- The pull request carries the fix, the helpers it needs, the DocPerm rows and patches it needs,
  fixes to its own regressions, and their tests. Refactors and unrelated bugs go in a separate pull
  request.
- A guard and the DocPerm rows it needs go in one commit. Apart, the guard commit is a regression.
- Match the surrounding code and the app's coding standards.
- Evidence (payloads, matrices, reproductions) goes in the report back, and the pull request
  describes only the change.
