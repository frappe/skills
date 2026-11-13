# The canvas page

`assets/harness/canvas/template.html` is the whole page; `build.mjs` only substitutes `__DATA__`. Change the template, not the built file. These are the decisions it embodies; keep them when you edit it, because each one came from a reviewer looking at the page and asking for it.

## Layout

- One lane per flow, stacked vertically in the order of `out/index.json`. Dagre lays each lane out left to right from the initial state. Forward edges are grey, back edges (to a state further left) are dashed accent, and every edge carries its event name.
- The first view is the first lane at readable size, not a fit of the whole world: fitting ten lanes makes every screenshot a thumbnail. "Fit" is a button.
- Pan by drag, zoom with ctrl or meta plus wheel, Safari gesture events and two-pointer pinch. Zoom goes through one rAF-batched `applyView`; pinch must feel immediate, so no easing and no per-event layout reads.
- Findings sit in a `<details>` at the top of their lane, next to the graph they describe.
- The app grid is `grid-template-rows: minmax(0, 1fr)` and the sidebar has `min-height: 0`. Without both, a long comment list makes the grid row grow past the window, the panel never overflows, and the sidebar cannot scroll, which is how the comments tab once got stuck.

## The lightbox is a tree walker

Clicking a screenshot opens it full size, and from there the arrow keys walk the flow's tree, not a flat list:

- Right follows an outgoing edge (the first, or the branch last taken from this state); Left goes to the parent; Up and Down move between the parent's other children; Esc closes.
- A breadcrumb shows the path from the initial state with the event on each hop; crumbs are clickable.
- A choices row under the screenshot lists "→ next" (the branch Right will take is outlined), "↕ instead" (siblings) and "↩ also" (non-tree edges out of this state, such as CLEAR_SEARCH back to the list).
- The canvas behind pans to the current state, rings its card, and draws the edge just taken in the `--hot` colour, so closing the lightbox leaves you standing on it.

The tree is a breadth-first walk from the initial state over the machine's edges in manifest order. The first edge to reach a state is its tree edge; the rest show under "also". Every state nothing points at is a root too, and an initial state with no edges at all (the graph library leaves out `always` transitions) is joined to the next root with an `always` hop. Uncaptured states are skipped through to their first captured descendant.

## Layout rules the lightbox must keep

- The main column is a grid: header, description, `minmax(0, 1fr)` stage, choices row, footer. Every control stays on screen at any viewport; the screenshot takes what is left.
- The image's max height is `--shot-h`, set by a ResizeObserver on the stage. A fixed `calc(100dvh - N)` breaks the moment a row is added, which is how the controls ended up below the fold once.
- The header holds the breadcrumb only; the flow title is its muted prefix. Nothing repeats the state name.
- `<meta charset="utf-8">` stays at the top so the page also renders locally; the publish wrapper adds its own, harmlessly.

## Comments

Pins are fractions of the screenshot, stored in the artifact's `comments` collection, so a republish with the same `flow/state` ids keeps every pin in place. The sidebar's Comments tab lists them all; "Copy prompt" turns the open ones into Markdown for the review loop. The page works read-only without the `db` capability and says so.

## Check before publishing

```sh
node scripts/smoke.mjs <build dir> <flow> <state> [keys…]
```

It serves the build dir, opens the lane, clicks the state, presses the keys (default: Right, Down, Left) and prints where each landed plus any page errors; `smoke-lightbox.png` and `smoke-canvas.png` land beside the build dir. Run it from the repo's Playwright folder so `@playwright/test` resolves, and look at both PNGs: the lightbox with every control visible, the canvas with the current card ringed.
