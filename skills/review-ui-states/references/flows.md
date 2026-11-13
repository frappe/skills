# Writing a flow

A flow is an XState machine plus the browser steps that realise it: `enter` brings a fresh scene to the initial state, and `events[EVENT]` performs one interaction and waits for the target state. `capture.spec.ts` walks `createTestModel(machine).getShortestPaths()`, opening a new scene per path, and screenshots each state the first time a path reaches it. Read `assets/example/listing.ts` once; copy its shape, not its imports or API paths, which belong to the example app.

## Naming states

Name states for what the user sees, not for the code's variables: `skeleton`, `failed`, `searchEmpty`, `moveAccessWiden`, `lockedOut`. Every state gets `meta.description`, one sentence in plain English; the canvas shows it under the screenshot and it is what the reviewer reads before looking.

List states by reading the component tree the flow covers and asking, for each branch and each request it makes: what shows before the response, what shows on failure, what shows when the result is empty, and what shows while a write is in flight. Those four questions find most of the states that nobody screenshots by hand.

Events are named for what the user or the world does: `LOADS`, `FAILS`, `RETRY`, `SEARCH_MISS`, `PICK_FIVE`, `CHUNK_FAILS`. One event per edge; the canvas draws the name on the arrow.

Keep a machine flat and keep one flow to one concern. A second presentation (grid, phone width) is its own states or its own flow, not a parallel region.

## Reaching states the UI does not offer

`scene.hold(urlGlob)` intercepts matching requests and returns `{release, abort}`:

- **Loading, skeleton, busy, mid-flight**: hold the request, trigger the action, screenshot, then `release()` in the next event step.
- **Failed**: `abort()` fulfils the held request and every later match with a 500 until `release()`. The transport retries server errors with backoff, so a single aborted request never reaches the UI's failed state.
- **Retry**: `release()` first, then click Retry.
- **Shaped responses** (a full quota, an expired link, a stale version): `page.route` the request and fulfil it with a modified body; that is allowed when the API offers no way to create the condition.

For states that need another user (a share received, a lowered own access), seed with an API context signed in as the peer: `await scene.as(scene.people.peer)`.

For states a signed-out visitor sees, open a second browser context without the actor's cookies; keep it in a `WeakMap` keyed by scene so it closes with the scene.

Set `meta.transient: true` on a state that cannot be screenshotted reliably or cannot be reached on this site, and say why in the description. It stays in the graph as a dashed pill, so the canvas still shows that the state exists.

## Making the screenshot show the right state

The capture takes the screenshot right after the event step returns and `settle()` passes, so the step must end on an `expect` that only the target state satisfies: the empty-state title, the Retry button, the toast text, `N selected`. Waiting for a request alone is not enough; the DOM updates after it.

Use `settle[state]` for a state that needs longer than the default wait (a skeleton that must outlive the shell's boot splash) and `frame(scene, state)` to screenshot a region instead of the viewport (a dialog, a sidebar).

Seed through the API, not the UI: the shortest paths open a new scene per path, so `enter` runs once per path and must be fast and deterministic. Give the scene's workspace a readable name (`folderTitle`), because breadcrumbs appear in every screenshot.

Use realistic content: people with names, files called "Quarter review.pdf", not "test1". The reviewer judges the screenshots as if they were the product.

## Shortest-path quirks

- `getShortestPaths()` de-duplicates by prefix, so a state reachable from two parents is captured from the shorter one only; the manifest records `parent` and `via` for that path.
- An `always` transition on the initial state makes the first snapshot skip it; mark such a state transient and let the walk start from the next one.
- Paths are independent scenes. A state that depends on history (Recent, Starred, Trash having rows) must seed that history in `enter` or in the event step, not rely on an earlier path.
- `steps[0]` carries the event `xstate.init`; the harness skips it.

## Running

When runs share provisioned users (the example's global teardown deletes them), run one at a time per machine under a lock such as `flock /tmp/ui-states-capture.lock` (`flock` comes from util-linux; on macOS install it with Homebrew). `UI_STATES_FLOWS=a,b` limits a run to those flows. The run writes `out/<flow>.json` and `out/<flow>/<state>.png`, and `out/index.json` with the canvas order.

Done means: the run passes, every non-transient state has a screenshot, and you have looked at every PNG and each shows the state its description claims. Typecheck with the e2e suite's `tsc --noEmit`.

## Brief for a subagent

Give a flow-writing agent: the harness folder, the finished example flow, the run command with the lock, the source files the flow covers, the list of states you expect at minimum, the facts it cannot discover (site URL, routes, which users exist), and the report format: states captured, states unreachable and why, harness problems, and the implicit-state-machine findings with file paths and line numbers. Tell it to edit only its own flow files.
