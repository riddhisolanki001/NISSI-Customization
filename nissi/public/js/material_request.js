frappe.ui.form.on('Material Request', {
    validate(frm) {
        let seen = {};
        let duplicates = [];

        (frm.doc.items || []).forEach(row => {
            if (!row.item_code) return;

            if (!seen[row.item_code]) {
                seen[row.item_code] = [row.idx];
            } else {
                seen[row.item_code].push(row.idx);
            }
        });

        Object.keys(seen).forEach(item => {
            if (seen[item].length > 1) {
                duplicates.push(
                    `${item} in rows ${seen[item].join(', ')}`
                );
            }
        });

        if (duplicates.length) {
            frappe.validated = false;
            frappe.throw({
                title: __('Duplicate Items'),
                message: __('Same item found multiple times:<br>') + duplicates.join('<br>')
            });
        }
    }
});
