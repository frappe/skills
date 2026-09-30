---
id: A29
area: customization
mechanism: M15
---
# A29 — A Virtual DocType controller implements every method the framework calls

**Why:** A Virtual DocType has no table. The framework calls the controller for every operation it
would otherwise do in SQL. A missing method does not raise: the list view returns an empty list
and the user reports missing data.

## Bad

```python
# my_app/doctype/remote_order/remote_order.py
from frappe.model.document import Document


class RemoteOrder(Document):
	def load_from_db(self):
		super(Document, self).__init__(fetch_remote_order(self.name))

	def db_insert(self, *args, **kwargs):
		create_remote_order(self.as_dict())

	def db_update(self, *args, **kwargs):
		update_remote_order(self.name, self.as_dict())
```

## Good

```python
# my_app/doctype/remote_order/remote_order.py
import frappe
from frappe.model.document import Document


class RemoteOrder(Document):
	def load_from_db(self):
		super(Document, self).__init__(fetch_remote_order(self.name))

	def db_insert(self, *args, **kwargs):
		create_remote_order(self.as_dict())

	def db_update(self, *args, **kwargs):
		update_remote_order(self.name, self.as_dict())

	def delete(self):
		delete_remote_order(self.name)

	@staticmethod
	def get_list(filters=None, page_length=20, **kwargs):
		return fetch_remote_orders(filters, page_length)

	@staticmethod
	def get_count(filters=None, **kwargs):
		return count_remote_orders(filters)

	@staticmethod
	def get_stats(**kwargs):
		return {}
```

## Find

- DocType JSON with `"is_virtual": 1` in the app.
- For each, check the controller for `load_from_db`, `db_insert`, `db_update`, `delete`,
  `get_list`, `get_count`, and `get_stats`.
- `rg -n 'frappe\.get_all\(\s*["\x27]<virtual doctype>' --type py` across the bench.
- A child table on a virtual DocType.

## Confirm

`DatabaseQuery` returns `[]` when the controller has no `get_list`
(`frappe/model/db_query.py`). The list view is empty and no error is raised. This is the finding
that hides longest.

Bulk fetch raises for a virtual DocType. Lazy document loading falls back with a warning. Child
tables are not inserted or updated by the framework, so the controller owns them.

`frappe.get_all` and `frappe.db.get_value` go to the database and return nothing for a virtual
DocType. Every read must go through `frappe.get_doc` or the controller's `get_list`.

Making an existing standard DocField virtual is a different change and Customize Form refuses it
(`allow_property_change`). A virtual field has no column and is absent from `frappe.db` results.
