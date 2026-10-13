# Asking the user

Every `ask-user` finding from a step goes to the user in one plain chat message, never with a question tool such as AskUserQuestion. The user should be able to decide after one read, without the reviewer's text or the code open.

## One finding

1. **Header line:** number, a short title, the reviewer, and `file:line`.
2. **A scenario** in a short paragraph: a concrete person or system doing a concrete thing, and what goes wrong for them. Use real names from the product, not abstract terms.
3. **The options** as a lettered list. Each option is one or two plain sentences: what you would do, and what it means for the person in the scenario. Mark the one you recommend with "(recommended)" and say why in one sentence.

Write in plain paragraphs. Do not use tables. Add a short `diff` only when the whole fix is one or two lines and seeing it makes the choice clearer. Write each finding fresh. Do not paste the reviewer's description. The full description stays in the round comment ([verdict.md](verdict.md)).

End the message with one reply line: `Reply like: "1a, 2b", or "2 skip: <reason>".`

## Example

```markdown
### 2 decisions needed

**1 · `get_open_orders` returns orders the user cannot read** · correctness · `shop/api.py:42`

A customer logs in to the portal and opens the Orders page. They see every open Sales Order in the system, including other customers' orders, because the API reads orders without checking permissions.

a. Check read permissions (recommended). The customer sees only their own orders. The Orders page for staff stays the same, but a staff member without read access to Sales Order sees an empty list instead of all orders. This closes a data leak.

b. Leave it. Every logged-in user can keep listing every open order.

---

**2 · The discount rule is written twice, and the copies disagree** · taste · `shop/doctype/quotation/quotation.js:30`

A sales user enters 10 units on a Quotation. The form shows a 5% discount, because the server gives the discount from 10 units. They save, and the saved Quotation also has the discount. Then they change the quantity to 11. The form recalculates with its own copy of the rule, which starts at 12 units, and the discount disappears from the screen until they save again.

a. Calculate the discount only on the server (recommended). The form asks the server each time the quantity changes, so the screen always matches the saved document. There is one rule to change in future.

b. Keep both copies and make the JavaScript match the Python. A test with shared cases keeps them equal, but every future change to the rule has to be made twice.

Reply like: "1a, 2b", or "2 skip: <reason>".
```

## Decisions

Record every answer as a **decision**: the finding id, the chosen option, and the user's reason. Decisions go into every later subagent prompt and into the PR's `## Review` section, and nothing in the run reverses them.
