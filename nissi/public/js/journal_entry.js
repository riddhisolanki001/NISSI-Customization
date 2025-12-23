function has_cash_entry_role() {
    if (frappe.session.user === "Administrator") {
        return false;
    }

    const has_role = frappe.user.has_role('Cash Entry User');
    return has_role;
}

frappe.ui.form.on('Journal Entry', {
    onload(frm) {
        if (!frm._original_voucher_type_options) {
            const df = frappe.meta.get_docfield('Journal Entry', 'voucher_type');
            frm._original_voucher_type_options = df.options;
        }

        const has_cash_role = has_cash_entry_role();

        if (has_cash_role) {
            frm.set_df_property('voucher_type', 'options', ['Cash Entry']);
            frm.set_value('voucher_type', 'Cash Entry');
        } else {
            frm.set_df_property('voucher_type', 'options', frm._original_voucher_type_options);
        }

        frm.refresh_field('voucher_type');
    },

    refresh(frm) {
    const has_cash_role = has_cash_entry_role();

    if (has_cash_role) {
        const grid = frm.fields_dict['accounts'].grid;

        grid.get_field('account').get_query = function (doc, cdt, cdn) {
            const row = locals[cdt][cdn];

            if (!row.custom_type) {
                return {
                    filters: {
                        name: 'Account type not selected'  
                    }
                };
            }

            if (row.custom_type === 'Credit') {
                return {
                    query: 'nissi.py.filter.get_all_child_accounts',
                    filters: {
                        type: 'Credit',
                        company: frm.doc.company
                    }
                };
            }

            if (row.custom_type === 'Debit') {
                return {
                    query: 'nissi.py.filter.get_all_child_accounts',
                    filters: {
                        type: 'Debit',
                        company: frm.doc.company
                    }
                };
            }

            return {
                filters: {
                    name: '__invalid__'
                }
            };
        };

        (frm.doc.accounts || []).forEach(row => {
            if (!row.custom_type && row.account) {
                row.account = null;
            }
        });

        frm.refresh_field('accounts');
    }
}
});
