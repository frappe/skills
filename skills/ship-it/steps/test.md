# 4. Test (prod)

Prove the change works by driving the real product, the way a user would. Unit tests are CI's job. Run only the tests near the change, if any.

## Scenarios

Turn the intent into named scenarios: one per numbered item, skipping a `Must not` item that a user cannot hit. Name each with its item number (`intent #3`). Each scenario has steps and an expected result.

## Run them

Start the product the way this repo runs it: the dev server, the CLI, or the Frappe site on the bench. Drive each scenario:

- **Web UI**: drive it in a browser.
- **CLI or API**: run the commands.

## Evidence

Every live scenario produces evidence a reviewer can see in the PR without running anything:

- **Screenshot** a static result: a layout, a state, an error message. Capture before and after when the change alters something that existed.
- **Video** when the change is about motion or a sequence: an animation, a transition, drag and drop, a multi-step flow, focus or keyboard behavior. Record with the screen recorder your agent has. Where no recorder is available, take a screenshot of each key step instead. Keep videos short: the scenario only.
- **Transcript** for a CLI or API scenario: the command and the part of its output that proves the result, trimmed to what matters.

Save every file under `$TMPDIR/ship-it/<repo>-<branch>/`, outside the repo, named after its scenario (`02-minor-without-label.png`).

Mark a scenario **live** only when you drove it against the running product in this run. A unit test, a mock, or reading the code is not live. An honest "untested, because <reason>" is worth more than a guessed pass.

## Verdict

- **go**: every scenario passed live. Continue.
- **no-go**: a scenario failed. That is an `auto-fix` blocker: send it to a fixer subagent, re-run the scenario, up to 3 attempts.
- **inconclusive**: a scenario could not be driven (no running site, missing credentials, no UI). Ask the user: fix the setup, or continue with the gap noted in the PR.
- **no-surface**: the change has no user-visible surface (a refactor, internal tooling). Note it and continue.

**Done** when the verdict is go or no-surface, or the user accepted an inconclusive result. Every live scenario has its screenshot, video, or transcript saved for the PR's Evidence section.
