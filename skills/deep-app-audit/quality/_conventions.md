# Shared conventions for the quality rules

Every file in `quality/` follows this contract. A file never repeats what this file says.

The rules are documentation, not prompts. `_audit.md` turns one rule or one check into an audit
task. Because of this, no rule speaks to an agent. Rule text is declarative and in STE-100
Simplified Technical English.

The target is the `develop` branch of Frappe and its first-party apps.

## Kinds of file

- **Rule**: one reviewable practice. Lives in an area directory. The atom of this directory.
- **Mechanism page**: the good way to use one customization mechanism, with the rules that
  apply to it. Lives in `mechanisms/`.
- **Check**: a whole-surface analysis with a method, such as copy-paste drift from core. A check
  cannot be stated as one rule. Lives in `checks/`.

## Layout

```
quality/
  _conventions.md
  _audit.md
  A-customization/A01-<slug>.md
  B-correctness/B01-<slug>.md
  mechanisms/M01-<slug>.md
  checks/K01-<slug>.md
```

There are two areas: customization and correctness. A practice that is not in one of the two
areas is not a rule here.

There are no index files. The directory listing is the index.

## Identifiers

The file name is `<id>-<slug>.md`. The id is the area letter and two digits, `M` and two digits
for a mechanism page, or `K` and two digits for a check.

An id is a stable handle, not a position in a sequence. Gaps are allowed. When two rules merge,
the merged rule keeps one of the two ids and the other id is never used again. A rule that moves
to another area gets a new id and the old id is retired.

Cross-references use the id, never a path.

## Rule format

```markdown
---
id: B14
area: correctness
mechanism: M07
semgrep: {rules: [frappe-manual-commit], coverage: partial}
---
# B14 — Title in the imperative

**Why:** what breaks, and for whom.

**Applies to:** the condition that makes this rule relevant.

## Bad

## Good

## Find

## Confirm
```

Fields:

- `id` and `area` are always present. `area` is `customization` or `correctness`.
- `mechanism` is present when the rule is about one mechanism. It holds one mechanism id.
- `semgrep` is present only when a rule in the Frappe `semgrep-rules` repository checks the
  practice. `coverage` is `full` when the semgrep rule finds every case, or `partial` when it
  finds one case only or matches for a different reason. A partial rule still needs the `Find`
  section.

Body:

- **Why:** one or two sentences. Name the failure and who carries it.
- **Applies to:** optional. Use it only when the rule does not apply to every app. An agent that
  reads a rule and finds no match must be able to stop.
- `## Bad` and `## Good`: short code examples, written for these files.
- `## Find`: the search signals that find candidates, usually `rg` patterns and code shapes.
- `## Confirm`: how to tell a true positive from a false positive. Semgrep also gives false
  positives, so a rule with a semgrep rule still has this section.

There is no version field. The rules describe `develop`. When the behaviour on an older version
is different and the difference changes the risk, `## Confirm` states it in one line.

An audit reads code. It does not run the app, and it does not measure. `## Confirm` states a test
that a reader applies by reading, such as a shape in the code or a property of the schema. A
practice that only a measurement can confirm is not a rule.

## Mechanism page format

```markdown
---
id: M07
---
# M07 — Mechanism name

**What:** what the framework lets an app do here.

**Guards:** the invariants core keeps, and what removes them.

## Good use

## Rules
```

`## Good use` comes before `## Rules`. A mechanism page describes the correct use first, then
lists the rules that apply, by id. The link from a rule to a mechanism page is the `mechanism`
field.

## Check format

```markdown
---
id: K01
---
# K01 — Check name

**Kind:** whole-surface check. State what it is not.

**Why:** why the result matters.

## Task

## Inputs

## Output
```

`## Task` is numbered steps. `## Output` is the table the check produces. A check has no
examples and no search signals, because it has no single code shape.
