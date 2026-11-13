# Implicit state machines

Writing a flow's machine forces you to name every screen. The code usually does not: it decides the screen from several refs read in order. A finding records one such place so that the machine can later move into the code.

## What counts

Look for these shapes in the components and composables the flow covers:

- **A `v-if` chain over independent signals.** `isBlank`, then `error && !rows.length`, then `!rows.length`, then the list: four booleans, no name for the phase, and a new case has to be fitted into the chain by hand.
- **Two places deciding the same thing.** A Proxy picks which query is active on one condition, and a held-rows helper keys on a hand-joined string of five refs; they can disagree.
- **Flags that can both be true with no defined screen.** `dialog = 'rename'` while `selection.length === 0`; `uploading` and `failed` on the same row.
- **The same empty screen for different causes.** One empty component whose copy is reconstructed from whichever filter happens to be set.
- **A status string plus booleans beside it.** `status: 'ready' | 'refused'` and a separate `loading` ref that the status should have covered.
- **Timers as state.** A skeleton delay, a toast's lifetime, a "done" that fades after N ms, held outside any model.

Explicit machines already in the code (an enum of upload states, a discriminated union for link access) are not findings; name them in the flow's `source` so the canvas credits them.

## What to write

`out/findings.json`, keyed by flow id:

```json
{
	"listing": [
		{
			"title": "The listing phase is a v-if chain, not a value.",
			"detail": "FilesListing.vue picks blank, failed, empty, skeleton rows or real rows from four signals read in order: isBlank, loading, query.error and query.rows.length. Nothing names the phase.",
			"fix": "Derive one `phase` union ('blank' | 'skeleton' | 'failed' | 'empty' | 'rows') and render from it. The machine in flows/listing.ts is that union with its transitions."
		}
	]
}
```

`title` is one sentence stating the problem. `detail` names the files and the refs, and says what can go wrong. `fix` is the explicit state you would introduce, in one or two sentences; the flow's machine is usually that state's transition table, so say so.

Verify every claim by reading the code, not the agent's report. A finding that reverses which path keeps rows and which restarts the skeleton goes on the canvas as fact and costs trust. Three accurate findings per flow are worth more than eight plausible ones.
