---
id: M32
---
# M32 — Timeline and heatmap

**What:** The `additional_timeline_content` hook adds entries to the activity timeline of a
form. `get_timeline_data` on the doctype module feeds the heatmap that the form shows above the
timeline.

**Guards:** The hook is a dict keyed by doctype, and the `*` key. The `*` methods run before the
doctype methods. Each method is called with the doctype and the document name, and its result is
extended onto the list, so it must return a list or nothing; any other value raises.
`get_timeline_data` is read from the doctype module and is skipped when the doctype is custom.
Both run while the form is loading, in the same request as the document.

## Good use

The timeline is the place for an event that the user needs next to the document and that is not
a document of its own: a call from a telephony integration, a delivery status from a carrier, a
step of an external approval.

```python
def get_timeline_content(doctype, docname):
    return [
        {
            "doctype": "Fleet Trip Event",
            "creation": event.creation,
            "content": event.description,
        }
        for event in get_events(doctype, docname)
    ]
```

Return an empty list when there is nothing to add. Returning `None` is accepted, and returning a
dict or a string is not.

Bound the query. The method runs on every form load of the doctype, and a method registered under
`*` runs on every form load on the site. Read one indexed set of rows, with a limit, and read no
more.

The heatmap counts are a second query on the same load. Give the doctype a heatmap only when the
count is cheap and the user reads it.

## Rules

- A25 — A hook handler accepts every argument the call site passes
- A26 — A hook handler returns what the call site expects
