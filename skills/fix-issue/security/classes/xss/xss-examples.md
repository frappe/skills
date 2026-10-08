# Published XSS fixes, by shape

Each is a published GitHub Security Advisory with its merged fix. Read the PR for the full diff.

## A record name in a report formatter `href` — GHSA-f99r-gp2w-xghj

`erpnext/manufacturing/report/production_plan_summary/production_plan_summary.js`, `formatter`.
Fix: [frappe/erpnext#58273](https://github.com/frappe/erpnext/pull/58273).

```diff
 if (column.fieldname == "item_code") {
 	var color = data.pending_qty > 0 ? "red" : "green";
-	value = `<a style='color:${color}' href="/app/item/${data["item_code"]}" data-doctype="Item">${data["item_code"]}</a>`;
+	value = `<a style='color:${color}' href="${frappe.utils.get_form_link(
+		"Item",
+		data["item_code"]
+	)}" data-doctype="Item">${frappe.utils.escape_html(data["item_code"])}</a>`;
 }
```

## Many fields of a row into one HTML template — GHSA-m6x2-278g-pv2g

`erpnext/selling/page/point_of_sale/pos_item_selector.js`, `get_item_html`.
Fix: [frappe/erpnext#55503](https://github.com/frappe/erpnext/pull/55503). Escape every string field
once, then destructure. And replace the legacy `escape()`, which was URL encoding.

```diff
-const { item_image, serial_no, batch_no, barcode, actual_qty, uom, price_list_rate } = item;
+function sanitize_item_data(item) {
+	return Object.fromEntries(Object.entries(item).map(([key, value]) => [
+		key, typeof value === "string" ? frappe.utils.escape_html(value) : value,
+	]));
+}
+const { item_code, stock_uom, item_name, item_image, serial_no, ... } = sanitize_item_data(item);
-	data-item-code="${escape(item.item_code)}" ... title="${item.item_name}">
+	data-item-code="${item_code}" ... title="${item_name}">
```

## Saved filter values into jQuery-built rows — GHSA-hxfh-hh23-fvch

`frappe/desk/doctype/dashboard_chart/dashboard_chart.js`.
Fix: [frappe/frappe#41595](https://github.com/frappe/frappe/pull/41595).

```diff
 const filter_row = $(`<tr>
-		<td>${filter[1]}</td>
-		<td>${filter[2] || ""}</td>
-		<td>${filter[3]}</td>
+		<td>${frappe.utils.escape_html(filter[1])}</td>
+		<td>${frappe.utils.escape_html(filter[2] || "")}</td>
+		<td>${frappe.utils.escape_html(filter[3])}</td>
 	</tr>`);
```

## Guest text copied into a staff-visible record — GHSA-rv4r-c8v3-3hrc

`erpnext/crm/doctype/appointment/appointment.py`, Lead creation from a guest booking.
Fix: [frappe/erpnext#57947](https://github.com/frappe/erpnext/pull/57947). Escaped **at storage**, on
the one hop where guest input becomes staff-visible. The notes template (the sink) is unchanged.

```diff
+from frappe.utils.html_utils import escape_html
 if self.customer_details:
 	lead.append(
 		"notes",
-		{"note": self.customer_details, "added_by": frappe.session.user, "added_on": now()},
+		{
+			"note": escape_html(self.customer_details),
+			"added_by": frappe.session.user,
+			"added_on": now(),
+		},
 	)
```

## Other shapes and their fixes

| Shape | Fix |
|---|---|
| Desk microtemplate attribute: `data-name="{{ row.name }}"` | `{{ frappe.utils.escape_html(row.name) }}`. For a value used several times, bind once with `{% const n = frappe.utils.escape_html(row.name); %}` |
| A whitelisted `get_data` returning names that a microtemplate writes into attributes | escape the dict in Python before returning it, and remove the template-side escape |
| Portal / `www` / print / email Jinja: `<img src="{{ user.user_image }}">` | `{{ value \| e }}` on every attribute value |
| `frappe.throw(__("… {0}", [get_form_link("Item", code, true)]))` | escape each argument before `__()`, and pass an escaped `display_text` |
| SPA: `dangerouslySetInnerHTML={{ __html: _("… {0}", [`<strong>${v}</strong>`]) }}` | render translated strings through a renderer that does not pass raw HTML |
