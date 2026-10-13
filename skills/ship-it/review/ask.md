# Asking the user

Every `ask-user` finding from a step goes to the user in one plain chat message, never with a question tool such as AskUserQuestion. The user should be able to decide from a glance at each finding, without reading the reviewer's text.

## One finding

1. **Header line:** number, a short title, the reviewer, and `file:line`.
2. **The problem** in one sentence: what goes wrong, and for whom.
3. **One visual**, the smallest that shows the point:
   - a `diff` when the fix is a small code change;
   - a table when two things disagree: one row per difference, one column per side;
   - a flow line or a short call tree when the problem is in the order of calls: `install → build → pnpm not on PATH`.
4. **The options** as a table: letter, option, and what it changes. Put a related finding that one option fixes and another does not in its own column. Mark the one you recommend.
5. **Your note**, when you have one, in one line.

No paragraph longer than two lines. Write each finding fresh; do not paste the reviewer's description. The full description stays in the round comment ([verdict.md](verdict.md)).

End the message with one reply line: `Reply like: "1a, 2b", or "2 skip: <reason>".`

## Example

````markdown
### 2 decisions needed

**1 · `get_open_orders` returns orders the user cannot read** · correctness · `shop/api.py:42`

Any logged-in user can list every open Sales Order, including other customers' orders.

```diff
- return frappe.get_all("Sales Order", filters={"status": "Open"})
+ return frappe.get_list("Sales Order", filters={"status": "Open"})
```

|         | Option     | Effect                                                            |
| ------- | ---------- | ----------------------------------------------------------------- |
| **a** ✓ | `get_list` | Applies read permissions. Portal users see only their own orders. |
| **b**   | Leave it   | Every caller sees every open order.                               |

The reviewer marked this auto-fix; I am asking because **a** changes what the Orders page shows today.

---

**2 · The discount rule is in the controller and in the form script, and the copies disagree** · taste · `shop/doctype/quotation/quotation.js:30`

The form can show one total while the saved Quotation has another.

| Rule                              | `quotation.py`        | `quotation.js` |
| --------------------------------- | --------------------- | -------------- |
| Minimum quantity for the discount | 10                    | 12             |
| Rounding                          | `flt(..., precision)` | `Math.round`   |
| Discount on free items            | no                    | yes            |

|         | Option                          | Effect                                                                | Also fixes c3 (stale total after save) |
| ------- | ------------------------------- | --------------------------------------------------------------------- | -------------------------------------- |
| **a** ✓ | Form calls a whitelisted method | One copy of the rule, on the server. One request per quantity change. | yes                                    |
| **b**   | Keep both, match Python         | Two copies, kept equal by a test with shared cases.                   | no                                     |

Reply like: "1a, 2b", or "2 skip: <reason>".
````

## Decisions

Record every answer as a **decision**: the finding id, the chosen option, and the user's reason. Decisions go into every later subagent prompt and into the PR's `## Review` section, and nothing in the run reverses them.
