---
id: M28
---
# M28 — Workflow and `workflow_methods`

**What:** A Workflow record holds the states and transitions of a doctype. A transition can
carry Workflow Transition Task rows. The `workflow_methods` hook adds named tasks to the set a
transition can choose from, as `{"name": ..., "method": ...}` entries.

**Guards:** Tasks are matched by `name`. The framework checks the built-in
`DEFAULT_WORKFLOW_TASKS` names, `Webhook` and `Server Script`, before it reads the hook map, so
an entry that reuses one of those names is never reached. The hook map is a dict built from the
merged list, so two apps that declare the same name leave one entry and the last app wins. A
name that no entry matches throws. Enabled task rows are read in `idx` order. Every synchronous
task runs first, in that order, and shares the transaction of the transition. The asynchronous
tasks are then enqueued with `enqueue_after_commit`. All tasks run before the document is saved,
submitted or cancelled for the new state.

## Good use

A workflow task is the place for the side effect of a transition: create the follow-up document,
send the external notification, stamp an approval record. The state change itself stays in the
Workflow record, where a site can read it.

Name the task for the user who picks it in the transition row, and prefix the name so it stays
readable next to the built-in tasks and next to another app's tasks.

```python
workflow_methods = [
    {"name": "Fleet: create delivery trip", "method": "fleet.workflow.create_delivery_trip"},
]
```

The method takes the document, which still carries the old state. A synchronous task runs inside
the transition's transaction, so it must not commit and must not roll back: a failure there
fails the transition, which is what the user expects.

Mark a task asynchronous when it is optional or slow. It is then enqueued after the commit, so
it sees the document in its new state, and its failure does not fail the transition.

A task that must run for every save, and not only for a transition, belongs in the controller or
in `doc_events` instead. A workflow covers the transitions a workflow defines and nothing else.

## Rules

- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve
- A25 — A hook handler accepts every argument the call site passes
- B01 — Do not commit or roll back inside document lifecycle code
- B04 — Enqueue a job after commit when it reads what the request wrote
