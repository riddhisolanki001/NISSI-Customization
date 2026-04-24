frappe.ui.form.on('Payment Entry', {
    refresh(frm) {
        if (frm.doc.docstatus !== 1) return;

        let mode_of_payment = frm.doc.mode_of_payment;

        if (mode_of_payment && mode_of_payment.includes('CHEQUE')) {
            // Make posting_date editable ONLY for CHEQUE
            frm.set_df_property('posting_date', 'read_only', 0);
            frm.refresh_field('posting_date');
        } else {
            // Keep posting_date read-only for non-CHEQUE payments
            frm.set_df_property('posting_date', 'read_only', 1);
            frm.refresh_field('posting_date');
        }

        let account = null;
        if (frm.doc.payment_type === "Receive") {
            account = frm.doc.paid_to;
        } else if (frm.doc.payment_type === "Pay") {
            account = frm.doc.paid_from;
        }
        console.log("Account for check:", account);
        frappe.call({
            method: "nissi.py.repost_account_ledger.check_account_against_latest_bank_gl",
            args: {
                doctype: frm.doc.doctype,
                docname: frm.doc.name,
                account: account
            },
            callback: function (r) {
                // show button only if return is false
                if (r.message === true
                ) {
                    frm.add_custom_button(__('Repost Account Ledger'), function () {

                        if (frm.is_dirty()) {
                            frappe.throw(__('Please save the document before reposting the Account Ledger.'));
                        }

                        frappe.call({
                            method: "nissi.py.repost_account_ledger.repost_ple_for_voucher",
                            args: {
                                voucher_type: frm.doc.doctype,
                                voucher_no: frm.doc.name
                            },
                            freeze: true,
                            callback: function () {
                                frappe.msgprint(__('Repost initiated for this Payment Entry.'));
                                setTimeout(function () {
                                    frm.reload_doc();
                                }, 500);
                            }

                        });
                    });
                }
            }
        });
    }
});
