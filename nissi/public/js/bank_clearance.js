frappe.ui.form.on("Bank Clearance", {
	refresh: function (frm) {
		// Add custom button to fetch clearance entries
		if (!frm.is_new()) {    
			frm.add_custom_button(__("Get Clearance Entries"), function () {
                if (!frm.doc.account){  
                    frappe.msgprint({
                        title: __("Missing Field"),
                        indicator: "red",
                        message: __("Please set <b>Account</b> to fetch clearance entries.")
                    });
                    return;
                }
				get_clearance_entries(frm);
			});
		}
	},

	custom_clearance_start_date: function (frm) {
		validate_dates(frm);
	},

	custom_clearance_end_date: function (frm) {
		validate_dates(frm);
	}
});

function validate_dates(frm) {
	// Show payment entries table only if both dates are set
	if (frm.doc.custom_clearance_start_date && frm.doc.custom_clearance_end_date) {
		if (frm.doc.custom_clearance_start_date > frm.doc.custom_clearance_end_date) {
			frappe.msgprint(__("Clearance Start Date must be before Clearance End Date"));
			return false;
		}
		frm.get_field("payment_entries").$wrapper.show();
		return true;
	}
	return false;
}

function get_clearance_entries(frm) {
	// Validate required fields
	if (!frm.doc.account) {
		frappe.msgprint({
			title: __("Missing Field"),
			indicator: "red",
			message: __("Please set <b>Account</b>")
		});
		return;
	}

	if (!frm.doc.custom_clearance_start_date) {
		frappe.msgprint({
			title: __("Missing Field"),
			indicator: "red",
			message: __("Please set <b>Clearance Start Date</b>")
		});
		return;
	}

	if (!frm.doc.custom_clearance_end_date) {
		frappe.msgprint({
			title: __("Missing Field"),
			indicator: "red",
			message: __("Please set <b>Clearance End Date</b>")
		});
		return;
	}

	// Validate date range
	if (frm.doc.custom_clearance_start_date > frm.doc.custom_clearance_end_date) {
		frappe.msgprint({
			title: __("Invalid Date Range"),
			indicator: "red",
			message: __("<b>Clearance Start Date</b> must be before <b>Clearance End Date</b>")
		});
		return;
	}

	// Show loading
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Payment Entry",
			filters: [
				["Payment Entry", "clearance_date", ">=", frm.doc.custom_clearance_start_date],
				["Payment Entry", "clearance_date", "<=", frm.doc.custom_clearance_end_date],
				["Payment Entry", "docstatus", "=", 1],
                ["Payment Entry", "paid_to", "=", frm.doc.account]
			],
			fields: [
				"name",
				"payment_type",
				"party_type",
				"party",
				"posting_date",
				"clearance_date",
				"paid_amount",
				"status",
				"mode_of_payment",
				"reference_no",
				"reference_date",
				"remarks",
                "paid_to",
			],
			order_by: "clearance_date asc",
			limit_page_length: 500
		},
		callback: function (r) {
			if (r.message) {
				if (r.message.length === 0) {
					frappe.msgprint({
						title: __("No Records Found"),
						indicator: "orange",
						message: __("No Payment Entries found with clearance date between {0} and {1}",
							[frm.doc.custom_clearance_start_date, frm.doc.custom_clearance_end_date]
						)
					});
					frm.clear_table("payment_entries");
					frm.refresh_field("payment_entries");
					return;
				}

				// Clear existing rows
				frm.clear_table("payment_entries");

				// Add fetched payment entries to the table
				let total_amount = 0;
				r.message.forEach((entry) => {
					let row = frm.add_child("payment_entries", {
                        payment_document: "Payment Entry",
						payment_entry: entry.name,
						against_account: entry.paid_to,
						amount: entry.paid_amount,
						posting_date: entry.posting_date,
                        cheque_number: entry.reference_no,
						cheque_date: entry.reference_date,
						clearance_date: entry.clearance_date,
					});
					total_amount += (entry.paid_amount || 0);
				});

				frm.refresh_field("payment_entries");

                let formatted_total = "₹ " + total_amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");

				// Show success message with summary
				frappe.msgprint({
					title: __("Payment Entries Fetched"),
					indicator: "green",
					message: __("Fetched <b>{0}</b> Payment Entries<br>Total Amount: <b>{1}</b>",
						[r.message.length, formatted_total]
					)
				});
			}
		},
		error: function (err) {
			frappe.msgprint({
				title: __("Error"),
				indicator: "red",
				message: __("Error fetching payment entries. Please try again.")
			});
			console.error(err);
		}
	});
}