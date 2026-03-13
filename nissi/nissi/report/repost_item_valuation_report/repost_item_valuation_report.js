frappe.query_reports["Repost Item Valuation Report"] = {
	filters: [
		{
			fieldname: "item_code",
			label: "Item",
			fieldtype: "Link",
			options: "Item",
			default: "",
		},
		{
			fieldname: "warehouse",
			label: "Warehouse",
			fieldtype: "Link",
			options: "Warehouse",
			default: "",
		},
		{
			fieldname: "repost_status",
			label: "Repost Status",
			fieldtype: "Select",
			options: "\nCompleted\nFailed\nQueued\nIn Progress\nSkipped",
			default: "",
		}
	],

	onload: function (report) {
		report.page.add_inner_button("Clear Filter", function () {
			// Reset all filters to null/empty
			let filter_fields = ["item_code", "warehouse", "repost_status"];
			filter_fields.forEach((field) => {
				// if (field === "remaining_repost") {
				// 	frappe.query_report.set_filter_value(field, 0);
				// } else {
				frappe.query_report.set_filter_value(field, null);
				// }
			});

			// Refresh the report
			frappe.query_report.refresh();
		});

		report.page.add_inner_button("Go To Repost Item Valuation", function () {
			let doc_url = frappe.urllib.get_full_url("/app/repost-item-valuation");
			window.open(doc_url, "_blank");
		});

		report.page.add_inner_button("Repost Failed Items", function () {

			frappe.confirm(
				"Repost ALL Failed Item Valuations?",
				async function () {

					const res = await frappe.call({
						method: "nissi.nissi.report.repost_item_valuation_report.repost_item_valuation_report.repost_failed_items",
						freeze: true,
						freeze_message: "Reposting all failed items..."
					});

					if (res.message) {
						frappe.msgprint(`Reposted ${res.message.count} items`);
						frappe.query_report.refresh();
					}
				}
			);

		});
	}
};