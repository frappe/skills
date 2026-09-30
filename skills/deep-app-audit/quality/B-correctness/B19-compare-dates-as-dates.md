---
id: B19
area: correctness
---
# B19 — Compare dates as dates, and derive a period from the document date

**Why:** A date read from the database is a string in some paths and a `date` object in others.
A string comparison is a lexical comparison, and it gives a wrong answer across a format or a
year boundary. `NOW()` inside SQL uses the database session clock, not the site time zone, so a
cutoff computed in SQL is wrong for every site outside that zone. A period taken from a linked
document instead of from the document's own posting date puts the entry in the wrong month.

## Bad

```python
def is_overdue(invoice):
    return invoice.due_date < nowdate()          # string versus string

def get_period(invoice):
    return frappe.db.sql("select month(NOW())")  # the database clock, not the site clock
```

## Good

```python
from frappe.utils import getdate, nowdate, now_datetime

def is_overdue(invoice):
    return getdate(invoice.due_date) < getdate(nowdate())

def get_period(invoice):
    return getdate(invoice.posting_date).month
```

## Find

- `rg -n 'nowdate\(\)\s*[<>]|[<>]\s*nowdate\(\)' --type py`.
- `rg -n 'NOW\(\)|CURDATE\(\)|CURRENT_DATE' --type py` in raw SQL.
- `rg -n 'datetime\.(utcnow|now)\(' --type py`. Use `frappe.utils.now_datetime`.
- `rg -n 'nowdate\(\)|today\(\)' --type py` in code that creates or validates a transaction.
  A posting entry takes its period from `posting_date`, never from the system date.
- `rg -n 'getdate\(' --type py` on one side of a comparison and a bare field on the other.

## Confirm

Two values that both come from `getdate` or `get_datetime` compare correctly. A comparison
between two columns inside one SQL statement compares them as dates already. The finding is a
mix: one side parsed, the other side a string, or one side in the site time zone and the other
in the database session zone. `frappe.utils.get_datetime`, `add_days`, `getdate` and
`now_datetime` all work in the site time zone. `convert_utc_to_system_timezone` converts a
value that arrives from an external system.
