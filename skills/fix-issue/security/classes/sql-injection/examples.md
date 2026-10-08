# Published SQL-injection fixes, by shape

All are published GitHub Security Advisories with merged fixes. None of the commit subjects says
"SQL injection" — they read `refactor: use query builder …`, `fix: Add likely missing escapes`,
`refactor(stock): remove dead … branch`. Search code, not history.

## A caller-controlled `fields` list — GHSA-xp5c-86f4-7ppf

`erpnext/stock/doctype/stock_reservation_entry/stock_reservation_entry.py`,
`get_stock_reservation_entries_for_voucher`. Fix:
[frappe/erpnext#57968](https://github.com/frappe/erpnext/pull/57968).

```diff
 	sre = frappe.qb.DocType("Stock Reservation Entry")
 	query = (
-		frappe.qb.from_(sre)
+		frappe.get_query(sre, fields=fields, ignore_permissions=ignore_permissions)
 		.where((sre.docstatus == 1) & (sre.voucher_type == voucher_type) & (sre.voucher_no == voucher_no))
 		.orderby(sre.creation)
 	)
-
-	for field in fields:
-		query = query.select(sre[field])
```

The whitelisted function passes `ignore_permissions=False`. Internal callers use the private helper.
The version-15 backport added `frappe.has_permission(voucher_type, doc=voucher_no, throw=True)`,
because version-15's query engine has no permission mode.

## A caller-controlled `filters` key — GHSA-jp5q-723q-g826

`erpnext/controllers/queries.py`, `get_filtered_child_rows`. Fix:
[frappe/erpnext#57991](https://github.com/frappe/erpnext/pull/57991). This is the injection half
only: `get_query` keeps its default `ignore_permissions=True`.

```diff
 	table = frappe.qb.DocType(doctype)
 	query = (
-		frappe.qb.from_(table)
+		frappe.get_query(table, filters=filters)
 		.select(Concat("#", table.idx, ", ", table.item_code))
 		...
-	if filters:
-		for field, value in filters.items():
-			query = query.where(table[field] == value)
```

## One report filter written differently from its siblings — GHSA-wj7p-g62h-jh38

Sales Person Commission Summary report. Fix:
[frappe/erpnext#52640](https://github.com/frappe/erpnext/pull/52640).

```diff
 	for field in ["company", "customer", "territory"]:
 		if filters.get(field):
-			conditions.append(f"dt.{field}=%s")
-			values.append(filters[field])
-	if filters.get("sales_person"):
-		conditions.append("st.sales_person = '{}'".format(filters.get("sales_person")))
+			conditions.append(dt[field].eq(filters.get(field)))   # field from a literal list: safe
+	if filters.get("sales_person"):
+		conditions.append(st["sales_person"].eq(filters.get("sales_person")))
```

## A table name from a report filter — GHSA-x35x-4mvx-h959

Inactive Customers report. Fix: [frappe/erpnext#55627](https://github.com/frappe/erpnext/pull/55627).
Allow-list first, then the query builder.

```diff
+	if doctype not in {"Sales Order", "Sales Invoice"}:
+		frappe.throw(_("Invalid value {0} for 'Doctype'").format(doctype))
-	return frappe.db.sql(f"""select cust.name, ...
-		from `tabCustomer` cust, `tab{doctype}` so
-		where cust.name = so.customer and so.docstatus = 1 ...""", as_list=1)
+	C = frappe.qb.DocType("Customer")
+	DT = frappe.qb.DocType(doctype)
+	return (frappe.qb.from_(C).inner_join(DT).on(C.name == DT.customer)
+		.select(C.name, ...).where(DT.docstatus == 1).groupby(C.name)).run(as_list=True)
```

## A minimal escape patch across many string queries — GHSA-gwfr-5r8f-rwg4

Budget validation and ten sibling sites. Fix:
[frappe/erpnext#55574](https://github.com/frappe/erpnext/pull/55574).

```diff
-	condition = f"expense_account = '{params.expense_account}'"
+	condition = f"expense_account = {frappe.db.escape(params.expense_account)}"
-	condition += f" and parent.{date_field} between '{start_date}' and '{end_date}'"
+	condition += f" and parent.{date_field} between {frappe.db.escape(str(start_date))} and {frappe.db.escape(str(end_date))}"
 # status_updater.py, a no-op "escape" replaced:
-	args["cond"] = " or parent='%s'" % self.name.replace('"', '"')
+	args["cond"] = " or parent=%s" % frappe.db.escape(self.name)
```

`date_field` stays interpolated — safe only because code chooses it.

## A stored identifier, fixed at the writer — GHSA-h787-3x6w-8x4m

POS item search: a settings child table's `fieldname` values became columns in a search query.
Fix: [frappe/erpnext#58611](https://github.com/frappe/erpnext/pull/58611), in the settings
`validate()`:

```python
def validate_pos_search_fields(self):
	searchable_fields = {df.fieldname: df for df in get_searchable_item_fields()}  # from Item meta
	for field in self.pos_search_fields:
		if not searchable_fields.get(field.fieldname):
			frappe.throw(
				title=_("Invalid POS Search Field"),
				msg=_("Row #{0}: '{1}' cannot be used to search items.").format(field.idx, field.fieldname),
			)
```

The reader still interpolates the stored value, so reading the query alone reports this "unfixed".
Allow-listing at the reader as well is cheap.

## A SQL fragment accepted as a parameter — GHSA-v38v-9h2p-hr8v

A dict key `warehouse_condition` was concatenated into a `WHERE` clause. Fix:
[frappe/erpnext#58552](https://github.com/frappe/erpnext/pull/58552) deleted the branch.

```diff
-	elif previous_sle.get("warehouse_condition"):
-		conditions += " and " + previous_sle.get("warehouse_condition")
```
