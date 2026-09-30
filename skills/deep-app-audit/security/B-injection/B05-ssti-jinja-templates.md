# B05 — Server-Side Template Injection

**Scope:** user-controlled template *source* rendered by Jinja.

**Why:** a template compiled from user input is code execution.

## Find
- `rg -n "render_template|frappe\.render_template|get_template|Template\(|render_jinja" --type py`
- Any call where the first argument is a document field rather than a file path:
  Print Format HTML, Email Template `response`/`subject`, Notification message, Web Page
  `main_section`, Terms and Conditions, RFQ `message_for_supplier`, Statement of Accounts
  subject/body/`pdf_name`, Auto Repeat subject, naming series with `{}` expressions.
- Jinja evaluation inside autoname: `frappe.model.naming` expression handling.
- Client-supplied template strings on a whitelisted endpoint — always critical.

## Confirm
- Distinguish SSTI (attacker controls the template) from XSS (attacker controls the data).
  SSTI executes server-side and is a different severity class.
- Ask which role can write the field holding the template, and which context renders it.
  Low-role write plus high-role or system render is the finding.

## Report
Give a payload that reads a value proving server-side evaluation.
