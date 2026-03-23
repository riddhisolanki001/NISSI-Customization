// Copyright (c) 2025, Riddhi and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Repost Item Valuation Report"] = {
	filters: [
		{
			fieldname: "posting_date",
			label: "Date",
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
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
		},
		{
			fieldname: "remaining_repost",
			label: "Remaining Repost Only",
			fieldtype: "Check",
			default: 0,
		},
	],

	onload: function (report) {

		// Clear Filters Button (updated with date)
		report.page.add_inner_button(__("Clear Filters"), function () {
			let filter_fields = [
				"posting_date",
				"voucher_type",
				"voucher_no",
				"item_code",
				"warehouse",
				"repost_status",
				"remaining_repost"
			];

			filter_fields.forEach((field) => {
				if (field === "remaining_repost") {
					frappe.query_report.set_filter_value(field, 0);
				} else if (field === "posting_date") {
					frappe.query_report.set_filter_value(field, frappe.datetime.get_today());
				} else {
					frappe.query_report.set_filter_value(field, null);
				}
			});

			frappe.query_report.refresh();
		});

		//  Go To Repost Item Valuation
		report.page.add_inner_button(__("Go To Repost Item Valuation"), function () {
			let doc_url = frappe.urllib.get_full_url("/app/repost-item-valuation");
			window.open(doc_url, "_blank");
		});

		//  Repost Failed Items
		report.page.add_inner_button(__("Repost Failed Items"), function () {
			frappe.confirm(
				__("Repost All Failed Item Valuations?"),
				async function () {
					try {
						const res = await frappe.call({
							method: "nissi.nissi.report.repost_item_valuation_report.repost_item_valuation_report.auto_repost_item_valuation",
							freeze: true,
							freeze_message: __("Reposting all failed items..."),
						});

						if (res.message) {
							const { count, failed_count, failed_reposts } = res.message;

							let message = `<div style="padding: 10px;">
								<p><strong> Successfully Reposted:</strong> ${count} items</p>`;

							if (failed_count > 0) {
								message += `<p><strong>Failed to Repost:</strong> ${failed_count} items</p>
									<details style="margin-top: 10px;">
										<summary style="cursor: pointer; color: #d9534f;">View Failed Items</summary>
										<ul style="margin-top: 5px; max-height: 300px; overflow-y: auto;">`;

								failed_reposts.slice(0, 100).forEach((item) => {
									message += `<li>${item.item_code} - ${item.warehouse} (${item.posting_date} ${item.posting_time}): ${item.error}</li>`;
								});

								if (failed_reposts.length > 100) {
									message += `<li><strong>... and ${failed_reposts.length - 100} more</strong></li>`;
								}

								message += `</ul></details>`;
							}

							message += `</div>`;

							frappe.msgprint({
								title: __("Repost Status"),
								indicator: failed_count > 0 ? "orange" : "green",
								message: message,
							});

							frappe.query_report.refresh();
						}
					} catch (error) {
						frappe.msgprint({
							title: __("Error"),
							indicator: "red",
							message: __("Failed to repost items. Please try again."),
						});
						console.error("Repost error:", error);
					}
				}
			);
		});

	},
};