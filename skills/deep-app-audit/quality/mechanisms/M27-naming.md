---
id: M27
---
# M27 — Naming

**What:** A doctype gets its name from its `autoname` property, from an `autoname` method on the
controller, or from a naming series. The `naming_series_variables` hook adds a token to the
series language and maps it to a parser function.

**Guards:** `parse_naming_series` walks the dot-separated parts of the series. It handles a `#`
run first, then a token that a `naming_series_variables` hook claims, then the built-in date
tokens, then a fieldname of the document. A hook token is read as `[0]`, so the first app in the
list wins, and a hook that claims a built-in token such as `YY` takes it away from the framework
for every doctype on the site. The parser is called with the document and the token. Only one
`#` run in a series produces a counter. The DocType form warns when a doctype that is neither a
Single nor a child table has no naming rule and no `autoname` on its controller.

## Good use

Prefer a naming series or `format:` over a controller method. A series is data, so a site can
change the prefix without a deploy, and the counter is held in `tabSeries` where concurrent
inserts are safe.

Add a `naming_series_variables` token when the series needs a part that the framework cannot
derive: a fiscal year, a branch code, a company abbreviation. The parser takes the document and
the token, and returns a string.

```python
# hooks.py
naming_series_variables = {"FY": "fleet.naming.get_fiscal_year_code"}

def get_fiscal_year_code(doc, token):
    return get_fiscal_year(doc.transaction_date)[0][-2:]
```

Give the token a name that no built-in token uses, and a name specific enough that a second app
is unlikely to choose it. The hook is global: the token is available in every series on the
site, and the first app that claims it keeps it.

A controller `autoname` is for a name that is a function of the document and that a series
cannot express. It must keep a name that the caller already set, so an import or a retry writes
the record the caller asked for.

## Rules

- A14 — Every dotted path in `hooks.py` and `patches.txt` must resolve
- B05 — Check then insert is a race. Enforce uniqueness in the database
- B41 — A custom `autoname` must keep a name the caller already set
