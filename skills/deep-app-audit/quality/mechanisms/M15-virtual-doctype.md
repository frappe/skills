---
id: M15
---
# M15 — Virtual DocType

**What:** A DocType with `is_virtual` set has no table. The framework calls the controller for
every operation it would otherwise send to the database. The controller supplies
`load_from_db`, `db_insert`, `db_update`, `delete`, and, for the list and report views,
`get_list`, `get_count`, and `get_stats`. This lets an app present an external store as a
DocType, with the desk form, the list view, and the REST API on top of it.

**Guards:** `DatabaseQuery` returns an empty list when the controller has no `get_list`, so a
missing method looks like no data rather than an error. `frappe.get_all` and the other bulk
paths throw `Virtual DocType {0} cannot be fetched in bulk`. Lazy document loading is not
supported: the framework warns and falls back to the full controller. A Single Virtual DocType
does not use `tabSingles`. Child rows are not inserted or updated by the framework: `db_insert`
and `db_update` skip children when the parent is virtual. Deleting a document calls the
controller's own `delete`, and the framework throws when the controller did not define one. A
link field fetch on a virtual DocType goes through a full `frappe.get_doc`, not a
`frappe.db.get_value`.

## Good use

Implement the whole contract before you ship the DocType. A partly implemented controller fails
in the view the developer did not open.

```python
# my_app/doctype/remote_order/remote_order.py
from frappe.model.document import Document


class RemoteOrder(Document):
    def load_from_db(self):
        order = api.fetch_order(self.name)
        super(Document, self).__init__(order)

    def db_insert(self, *args, **kwargs):
        api.create_order(self.get_valid_dict())

    def db_update(self, *args, **kwargs):
        api.update_order(self.name, self.get_valid_dict())

    def delete(self):
        api.delete_order(self.name)

    @staticmethod
    def get_list(filters=None, page_length=20, **kwargs):
        return api.list_orders(filters=filters, limit=page_length)

    @staticmethod
    def get_count(filters=None, **kwargs):
        return api.count_orders(filters=filters)

    @staticmethod
    def get_stats(**kwargs):
        return {}
```

Honour the arguments the view passes. `get_list` receives the filters, the sort order, the page
length, and the start offset that the list view built. A controller that ignores `page_length`
and returns everything makes the list view unbounded, and the cost grows with the remote store.

Bound and cache the remote call. Every form load, every list page, and every link field fetch is
one call to the external system, on the web worker, inside the request. Set a timeout on it and
handle a failure with a clear message.

Do not use a Virtual DocType for data the site database can hold. It gives up the query builder,
the report view, joins, permissions on columns, and every performance tool the framework has.

Do not model child tables on a virtual parent. The framework does not write them.

## Rules

- A29 — A Virtual DocType controller implements every method the framework calls
