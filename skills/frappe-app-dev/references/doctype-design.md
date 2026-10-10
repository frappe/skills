# DocType Design

A DocType that saves data is not finished. Users see the form, the list, the link fields, and the permissions. Design each of these before you write the JSON. Then check the DocType against the checklist at the end of this file.

## 1. Decide before you write

Answer these questions first. Put the answers in the pull request or the design note.

1. Who uses this DocType? Name the roles.
2. What is the main task on the form? List the fields in the order the user fills them.
3. Which fields does the user type, and which fields does the system set?
4. Is the document a master (Customer, Item), a transaction (Invoice, Ticket), a log, or a setting?
5. Does the document need submit and cancel? A transaction that posts to a ledger usually does.
6. Can anyone delete it? Evidence, ledgers, and logs are usually never deleted.

## 2. Naming

The name is the primary key. Users see it in link fields, URLs, and print formats.

| Document kind | Use | Example |
| --- | --- | --- |
| Transaction | `naming_series:` with a short prefix and year | `SINV-.YYYY.-` |
| Master with a natural unique code | `field:<code_field>` | `field:item_code` |
| Master without a natural code | `naming_series:` or `format:` | `format:CUST-{#####}` |
| Log or system record | `hash` or `autoincrement` | Users do not open these |

- Do not use `hash` for a document that users open, search, or say aloud. A hash means nothing to a person.
- If the name is a code or a hash, set `title_field` to a readable field.
- Set `show_title_field_in_link: 1` so link fields show the title, not the code.
- Set `allow_rename: 1` only for masters where a rename is safe.
- For `format:` names that use field values, make sure those fields are mandatory and cannot change.

## 3. Field properties

### Labels and names

- Write `label` in Title Case: "Vehicle Plate", "Net Weight".
- Write `fieldname` in snake_case. Match the label: `vehicle_plate`, `net_weight`.
- Do not repeat the DocType name in the field name. Use `status`, not `ticket_status`.
- Add a `description` to each field whose meaning or unit is not obvious. Keep it to one short sentence.

### Type and value

- Use `Link` for a reference to another DocType. Do not store a name in a `Data` field.
- Use `Currency` for money. Set `options` to the currency field, for example `"options": "currency"`.
- Use `Float` with `precision` for weights and quantities. Use `Int` for counts.
- Set `non_negative: 1` on quantities and amounts that cannot be below zero.
- Set `unique: 1` on fields that must not repeat, such as an external ID.
- Set `default` where most documents use the same value.
- Write `Select` options in the form the user reads: `Draft\nPaid\nCancelled`.

### Behavior

| Property | Use it when |
| --- | --- |
| `reqd` | The document is invalid without the value. |
| `read_only` | The system computes or sets the value. Users must not type it. |
| `no_copy` | Duplicate must not copy the value: status, posted references, action dates, computed totals. |
| `set_only_once` | The value can be set on create but not changed after. |
| `allow_on_submit` | Users must edit the field after submit, such as a remark. |
| `depends_on` | Show the field only when it applies: `eval:doc.payment_type=='Cash'`. |
| `mandatory_depends_on` | The field is required only in some cases. |
| `read_only_depends_on` | The field locks after a state change: `eval:doc.status!='Draft'`. |
| `fetch_from` | Copy a value from a linked document: `customer.customer_name`. Add `fetch_if_empty` to keep user edits. |
| `search_index` | Users filter or sort the list by this field. |
| `bold` | The field is a key value that users scan for, such as a grand total. |
| `print_hide` | The field is internal and must not appear on the printout. |
| `hidden` | Use only for fields that no user ever needs to see. Prefer `depends_on`. |

- Set `no_copy` on every field that links to a posted document, such as `purchase_invoice` or `payment_entry`. A copy that keeps these links points to a document it did not create.
- Do not leave a computed field writable. If a controller sets it, make it `read_only`.

## 4. Form layout

Users read a form from top to bottom and left to right. Put fields in the order of the task.

1. Put the identity fields at the top: title, party, date, status.
2. Group related fields in a `Section Break`. Give each section a `label`.
3. Use `Column Break` for two columns. Do not use more than three columns.
4. Put each child table in its own section.
5. Put totals after the child table that they sum.
6. Put system fields in a last section: posted references, amendment links, audit values. Set `collapsible: 1` on it.
7. Use `Tab Break` when the form has more than about 25 visible fields. Put the main task on the first tab.

- Use `collapsible_depends_on` to open a collapsed section when it has a value.
- Do not put more than about eight fields in one section without a column break.
- Do not show a section that is empty in most states. Use `depends_on` on the section break.
- A form with no section breaks is a single long column. Users cannot scan it.

## 5. List view and search

The list view is the first screen most users see.

- Set `in_list_view: 1` on three to five fields. Pick the fields that tell one row from another.
- Set `in_standard_filter: 1` on the fields that users filter by: status, party, date, company, warehouse.
- Set `search_fields` to the fields users type in a link search: name, phone, code.
- Set `sort_field` and `sort_order`. Most transactions sort by `creation` or the posting date, descending.
- Set `in_global_search: 1` on fields that users search from the awesome bar.
- For a status field, add `<doctype>_list.js` with an indicator so each state has a color:

```javascript
frappe.listview_settings["Weighbridge Ticket"] = {
    add_fields: ["status"],
    get_indicator(doc) {
        const colors = { Draft: "gray", Held: "orange", Paid: "green", Voided: "red" };
        return [__(doc.status), colors[doc.status] || "blue", `status,=,${doc.status}`];
    },
};
```

### Child tables

- Set `in_list_view: 1` on the grid columns. These are the columns in the parent form.
- Set `columns` on each grid field. The sum must not be more than 10.
- Set `editable_grid: 1` on the child DocType so users edit rows in place.

## 6. Permissions

Write a role matrix before you write the `permissions` array. Add the matrix to the pull request.

| Role | Read | Write | Create | Delete | Submit | Cancel | Report | Export |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Operator | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| Supervisor | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 |
| Auditor | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |

- Give each role the smallest set of rights that its task needs.
- A read-only role, such as an auditor, gets `read`, `report`, `export`, and `print`. It does not get `write`, `create`, or `delete`.
- Do not give `delete` on transactions, ledgers, evidence, or logs. Use submit and cancel instead.
- Write each right as an explicit value. Do not copy one permission row to all roles and edit it later.
- Put sensitive fields at `permlevel: 1`. Then add a second permission row with `"permlevel": 1` for the roles that can see them:

```json
{ "role": "Accounts Manager", "permlevel": 1, "read": 1, "write": 1 }
```

- Use `if_owner: 1` when users must only see the documents they created.
- Use User Permissions on a `Link` field, such as `company` or `warehouse`, to limit rows per user.
- A child DocType has no permissions. It uses the permissions of the parent.

### Test the matrix

Tests that run as Administrator do not test permissions. Add a test for each role:

```python
frappe.set_user("auditor@example.com")
self.assertTrue(frappe.has_permission("Weighbridge Ticket", "read"))
self.assertFalse(frappe.has_permission("Weighbridge Ticket", "write"))
self.assertFalse(frappe.has_permission("Weighbridge Ticket", "delete"))
frappe.set_user("Administrator")
```

## 7. DocType settings

| Key | Use it when |
| --- | --- |
| `track_changes` | Users must see who changed what. Set it on masters, transactions, and settings. |
| `is_submittable` | The document posts or must lock after approval. |
| `quick_entry` | The master has few mandatory fields, so a dialog is enough to create it. |
| `allow_import` | Users load the records from a spreadsheet. |
| `image_field` | The document has a photo, such as an item or a person. |
| `max_attachments` | You must limit how many files a user attaches. |

## 8. Form actions

Users act on a document from its form. Do not make them open a list or call an API.

- Add a button in `<doctype>.js` for each state change: `frm.add_custom_button(__("Finalize"), ...)`.
- Show each button only in the states where the action is valid.
- Use `frm.set_query` to filter each `Link` field to valid values, such as enabled items or the same company.
- Use `frm.dashboard.add_indicator` or `frm.set_intro` to show the state and the next step.

## Checklist

Check each item before you merge a new or changed DocType.

- [ ] The name is readable, or `title_field` and `show_title_field_in_link` are set.
- [ ] Each field has a Title Case label and a matching snake_case field name.
- [ ] Each field with an unclear meaning or unit has a description.
- [ ] Each computed field is `read_only`.
- [ ] Status, posted references, action dates, and computed totals are `no_copy`.
- [ ] Conditional fields use `depends_on`, `mandatory_depends_on`, or `read_only_depends_on`.
- [ ] The form has labeled sections in task order. Long forms use tabs.
- [ ] System fields are in a last collapsible section.
- [ ] Three to five fields are in the list view. Standard filters are set.
- [ ] `search_fields` and `sort_field` are set.
- [ ] A status field has list indicators.
- [ ] Child grid columns are chosen, and their `columns` sum to 10 or less.
- [ ] A role matrix exists, and the `permissions` array matches it.
- [ ] No read-only role has `write`, `create`, or `delete`.
- [ ] No role can delete a transaction, ledger entry, evidence record, or log.
- [ ] Sensitive fields are at `permlevel: 1`.
- [ ] A test runs as each role and checks the matrix.
- [ ] The form has a button for each state change.
