import frappe


def execute(filters=None):
    columns = [
        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 300,
        },
        {
            "label": "Warehouse",
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 300,
        },
        {
            "label": "Repost Item Valuation",
            "fieldname": "repost_item_valuation",
            "fieldtype": "Link",
            "options": "Repost Item Valuation",
            "width": 200,
        },
        {
            "label": "Repost Status",
            "fieldname": "repost_status",
            "fieldtype": "Data",
            "width": 150,
        },
    ]

    # Build filters
    conditions = []
    conditions.append(f"based_on = 'Item and Warehouse'")
    if filters:
        if filters.get("item_code"):
            conditions.append(f"item_code = '{filters['item_code']}'")
        if filters.get("warehouse"):
            conditions.append(f"warehouse = '{filters['warehouse']}'")
        if filters.get("repost_status"):
            conditions.append(f"status = '{filters['repost_status']}'")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT
            item_code,
            warehouse,
            name AS repost_item_valuation,
            status AS repost_status
        FROM
            `tabRepost Item Valuation`
        {where_clause}
        ORDER BY item_code, warehouse
    """

    data = frappe.db.sql(sql, as_dict=True)

    # Report Summary
    total_records = len(data)
    total_completed = len(
        [row for row in data if row.get("repost_status") == "Completed"]
    )
    total_failed = len([row for row in data if row.get("repost_status") == "Failed"])
    total_queued = len([row for row in data if row.get("repost_status") == "Queued"])
    total_in_progress = len(
        [row for row in data if row.get("repost_status") == "In Progress"]
    )
    total_skipped = len([row for row in data if row.get("repost_status") == "Skipped"])

    report_summary = [
        {"value": total_records, "indicator": "Blue", "label": "Total Records"},
        {"value": total_completed, "indicator": "Green", "label": "Completed"},
        {"value": total_failed, "indicator": "Red", "label": "Failed"},
        {"value": total_queued, "indicator": "Orange", "label": "Queued"},
        {"value": total_in_progress, "indicator": "Yellow", "label": "In Progress"},
        {"value": total_skipped, "indicator": "grey", "label": "Skipped"},
    ]

    return columns, data, None, None, report_summary
