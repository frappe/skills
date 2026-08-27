# Testing

## File location

Tests live alongside the code they test:
```
apps/<app>/<app>/<module>/doctype/<doctype>/test_<doctype>.py
```

For feature-wise tests, place in the tests directory:
```
apps/<app>/<app>/tests/test_<feature>.py
```

## Writing tests

```python
import frappe
from frappe.tests import IntegrationTestCase

class TestExpense(IntegrationTestCase):
    def test_expense_creation(self):
        doc = frappe.get_doc(doctype="Expense", title="Test", amount=100)
        doc.insert()
        self.assertEqual(doc.amount, 100)

    def test_validation(self):
        doc = frappe.get_doc(doctype="Expense", title="Test", amount=-1)
        self.assertRaises(frappe.ValidationError, doc.insert)
```

Key patterns:
- Inherit from `frappe.tests.IntegrationTestCase` (not `unittest.TestCase`)
- Tests run inside a transaction that rolls back — no manual cleanup needed

## Unit tests (no database)

For pure logic that doesn't need Frappe context or database:

```python
from frappe.tests import UnitTestCase

class TestExpenseUtils(UnitTestCase):
    def test_calculate_tax(self):
        self.assertEqual(calculate_tax(100, 0.1), 10)
```

`UnitTestCase` is faster — no DB setup/teardown. Use for utility functions, calculations, parsing logic.

## Test fixtures

For test data that multiple tests need, create `test_records` or use `setUp`:

```python
class TestExpense(IntegrationTestCase):
    def setUp(self):
        self.category = frappe.get_doc(doctype="Expense Category", category_name="Travel").insert()
```

## Test site

Run tests on a **separate site** from the one the user is actively working on. Tests create, modify, and delete data — running them on the development site will pollute it.

Convention: if the dev site is `expense.localhost`, create `expense-test.localhost` for tests:
```bash
pilot new-site expense-test.localhost --admin-password admin
pilot install-app expense-test.localhost <app-name>
```

Always run tests against the test site:
```bash
pilot --site expense-test.localhost run-tests --app <app-name>
```

## Running tests

```bash
# All tests for an app
pilot --site <site> run-tests --app <app-name>

# Specific DocType
pilot --site <site> run-tests --doctype "Expense"

# Specific test file
pilot --site <site> run-tests --module <app>.<module>.doctype.<doctype>.test_<doctype>

# Specific test method
pilot --site <site> run-tests --module <app>.<module>.doctype.<doctype>.test_<doctype> --test test_expense_creation
```

## Common pitfalls

- If tests fail with "DocType not found", run `pilot --site <site> migrate` first.
- Test files must be named `test_*.py` to be discovered.
