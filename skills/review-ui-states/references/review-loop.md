# The review loop

The reviewer opens the canvas, clicks a screenshot, clicks where something is off, and types. Each pin becomes a document in the artifact's `comments` collection:

```json
{
	"flow": "dialogs",
	"state": "moveAccessWiden",
	"x": 0.626,
	"y": 0.484,
	"text": "should say \"Can view\", \"Can edit\", etc",
	"by": "u_…",
	"at": "2026-11-07T19:02:11.000Z",
	"done": false
}
```

`x` and `y` are fractions of the screenshot from the top-left; both are `null` for a note on the whole state. `by` is the viewer's opaque id; resolve names only for display, never store them.

Comments Claude writes during a review pass carry two optional fields. `kind` is `fix` (an obvious flaw with the solution in the text), `review` (a problem that needs a human decision) or `merge` (screens that differ in a few places and could be one); the page shows it as a tag, colours the pin, and filters on it. `related` lists other `flow/state` ids the comment also applies to; the page shows them as links. Write these with ArtifactData `batch` (`op: "set"`, a fresh id per comment, `by` set to the reviewer's id, read from one of their existing comments, so they can delete it) and end each text with a line such as "— Claude, for <reviewer name>" so readers can tell it from a human comment.

A reply is a document in the same collection with `parent` set to the id of the comment it answers, plus that comment's `flow` and `state`; it has no `x`, `y`, `kind` or `done`. The page shows replies under their comment, leaves them out of pins and counts, and deletes them with their comment. Done and Reopen apply to the comment, so a thread closes as a whole. Read replies before acting on a comment: a teammate may have objected or refined the fix.

## Getting the comments

- Pasted: the page's "Copy prompt" button produces Markdown grouped by flow and state, each line `- at (63%, 48%): text` or `- whole state: text`, with the screenshot path and the flow's source file in the headings. Done comments are left out unless the reviewer ticked "include done".
- Read directly: ArtifactData `list` on collection `comments` with the artifact url.

## Fixing in bulk

1. Group open comments by flow, then by source file. Several pins often point at one component.
2. For each pin, open `out/<flow>/<state>.png` and look at the position; the text is short because the pin carries the location. Read the component before deciding what "align the icon" means in code.
3. A comment that asks for a product decision rather than a fix ("redo this with information hierarchy layout") is a design task: do it, but show the before and after in the reply, since the reviewer commented on a screenshot and will judge the result on the next one.
4. After the fixes, recapture only the flows you touched, rebuild, republish to the same url, and look at the new screenshots for the commented states before reporting back.
5. Mark each handled comment `done: true` with ArtifactData `update` (pass `if_version` from the read). A comment you chose not to act on stays open; say why in the reply.

The page marks done comments green and drops them from the copied prompt, so the next round starts from what is still open.

## Keeping the canvas current

Screenshots are referenced by `flow/state.png`, so a republish with the same ids keeps every pin in place even when the pixels change. A renamed state orphans its comments; the sidebar still lists them with the old id, so rename deliberately and move the comments with `update` if they still apply.

The page lays flows out in the order of `out/index.json`, which the capture run writes from `flows/index.ts`; a flow not yet captured is simply absent, so publish early and republish per lane rather than waiting for every flow.
