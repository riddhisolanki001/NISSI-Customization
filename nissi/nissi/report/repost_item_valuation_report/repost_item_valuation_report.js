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
            options: "\nCompleted\nFailed\nQueued\nIn Progress",
            default: "",
        }
    ],

    onload: function(report) {
        report.page.set_title("Repost Item Valuation Report");

        // Container for summary cards
        report.summary_area = $('<div class="repost-summary d-flex mb-3"></div>').prependTo(report.wrapper);
    },

    on_refresh: function(report) {
        const grid = report.data_area.get_datatable();

        // Highlight rows by status
        if (grid) {
            grid.data.forEach(row => {
                const status = row.repost_status;
                if (status === "Failed") {
                    grid.set_row_style(row, {background: "#ffcdd2"}); // light red
                } else if (status === "Completed") {
                    grid.set_row_style(row, {background: "#c8e6c9"}); // light green
                } else if (status === "Queued") {
                    grid.set_row_style(row, {background: "#ffe0b2"}); // light orange
                } else if (status === "In Progress") {
                    grid.set_row_style(row, {background: "#fff9c4"}); // light yellow
                } else if (!status) {
                    grid.set_row_style(row, {background: "#e0e0e0"}); // grey for remaining
                }
            });
        }

        // Compute summary dynamically
        const data = grid ? grid.data : [];
        const total_records = data.length;
        const total_completed = data.filter(d => d.repost_status === "Completed").length;
        const total_failed = data.filter(d => d.repost_status === "Failed").length;
        const total_queued = data.filter(d => d.repost_status === "Queued").length;
        const total_in_progress = data.filter(d => d.repost_status === "In Progress").length;

        // Render summary cards
        const summary_html = `
            <div class="d-flex gap-3 flex-wrap">
                <div class="card p-2 bg-primary text-white">Total Records: ${total_records}</div>
                <div class="card p-2 bg-success text-white">Completed: ${total_completed}</div>
                <div class="card p-2 bg-danger text-white">Failed: ${total_failed}</div>
                <div class="card p-2 bg-warning text-dark">Queued: ${total_queued}</div>
                <div class="card p-2 bg-info text-dark">In Progress: ${total_in_progress}</div>
            </div>
        `;

        report.summary_area.html(summary_html);
    }
};