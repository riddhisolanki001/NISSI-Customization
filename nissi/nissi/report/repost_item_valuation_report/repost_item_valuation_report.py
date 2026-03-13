import frappe
from frappe.utils import now_datetime, nowdate

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
    conditions = ["based_on = 'Item and Warehouse'"]

    if filters:
        if filters.get("item_code"):
            conditions.append("item_code = %(item_code)s")

        if filters.get("warehouse"):
            conditions.append("warehouse = %(warehouse)s")

        if filters.get("repost_status"):
            conditions.append("status = %(repost_status)s")

    where_clause = " AND ".join(conditions)

    sql = f"""
    SELECT
        riv.item_code,
        riv.warehouse,
        riv.name AS repost_item_valuation,
        riv.status AS repost_status,
        riv.posting_date,
        riv.posting_time
    FROM
        `tabRepost Item Valuation` riv
    INNER JOIN (
        SELECT
            item_code,
            warehouse,
            MAX(CONCAT(posting_date,' ',posting_time)) AS latest_datetime
        FROM
            `tabRepost Item Valuation`
        WHERE {where_clause}
        GROUP BY item_code, warehouse
    ) latest
    ON
        riv.item_code = latest.item_code
        AND riv.warehouse = latest.warehouse
        AND CONCAT(riv.posting_date,' ',riv.posting_time) = latest.latest_datetime
    ORDER BY riv.item_code, riv.warehouse
    """

    data = frappe.db.sql(sql, filters, as_dict=True)

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


import frappe
from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import execute_repost_item_valuation

import frappe


import frappe
from frappe.utils import nowdate, nowtime


@frappe.whitelist()
def repost_failed_items():

    reposted = []

    conditions = ["based_on = 'Item and Warehouse'"]
    conditions.append("status = 'Failed'")

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            riv.item_code,
            riv.warehouse
        FROM
            `tabRepost Item Valuation` riv
        INNER JOIN (
            SELECT
                item_code,
                warehouse,
                MAX(CONCAT(posting_date,' ',posting_time)) AS latest_datetime
            FROM
                `tabRepost Item Valuation`
            WHERE {where_clause}
            GROUP BY item_code, warehouse
        ) latest
        ON
            riv.item_code = latest.item_code
            AND riv.warehouse = latest.warehouse
            AND CONCAT(riv.posting_date,' ',riv.posting_time) = latest.latest_datetime
    """

    data = frappe.db.sql(sql, as_dict=True)

    for row in data:
        try:
            doc = frappe.new_doc("Repost Item Valuation")

            doc.based_on = "Item and Warehouse"
            doc.item_code = row.item_code
            doc.warehouse = row.warehouse

            # set posting datetime to NOW
            doc.posting_date = nowdate()
            doc.posting_time = nowtime()

            doc.insert(ignore_permissions=True)
            doc.submit()
            execute_repost_item_valuation()
            reposted.append(doc.name)

        except Exception as e:
            frappe.log_error(
                f"Failed to create repost for {row.item_code} - {row.warehouse}: {str(e)}",
                "Repost Failed Items",
            )

    return {
        "count": len(reposted),
        "reposted": reposted
    }
