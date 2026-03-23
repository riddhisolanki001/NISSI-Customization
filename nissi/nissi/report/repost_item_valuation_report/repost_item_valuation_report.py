# Copyright (c) 2025, Riddhi
# For license information, please see license.txt

import frappe


def execute(filters=None):
    filters = filters or {}

    columns = get_columns()

    data = get_data(filters)

    #  SUMMARY ON FILTERED DATA
    total_records = len(data)

    total_completed = sum(1 for d in data if d.get("status") == "Completed")
    total_failed = sum(1 for d in data if d.get("status") == "Failed")
    total_queued = sum(1 for d in data if d.get("status") == "Queued")
    total_in_progress = sum(1 for d in data if d.get("status") == "In Progress")
    total_skipped = sum(1 for d in data if d.get("status") == "Skipped")
    total_remaining = sum(1 for d in data if d.get("status") == "Remaining")

    report_summary = [
        {"value": total_records, "indicator": "Blue", "label": "Total Records"},
        {"value": total_completed, "indicator": "Green", "label": "Completed"},
        {"value": total_failed, "indicator": "Red", "label": "Failed"},
        {"value": total_queued, "indicator": "Orange", "label": "Queued"},
        {"value": total_skipped, "indicator": "Grey", "label": "Skipped"},
        {"value": total_in_progress, "indicator": "Yellow", "label": "In Progress"},
        {"value": total_remaining, "indicator": "Purple", "label": "Remaining"},
    ]

    return columns, data, None, None, report_summary


# ---------------- COLUMNS ---------------- #
def get_columns():
    return [
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 120},
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
            "width": 250,
        },
        {
            "label": "Repost Item Valuation ID",
            "fieldname": "repost_item_valuation_id",
            "fieldtype": "Link",
            "options": "Repost Item Valuation",
            "width": 220,
        },
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
    ]


# ---------------- DATA ---------------- #
def get_data(filters):
    conditions = ["sle.docstatus = 1", "sle.is_cancelled = 0"]
    params = {}

    if filters.get("posting_date"):
        conditions.append("sle.posting_date = %(posting_date)s")
        params["posting_date"] = filters["posting_date"]

    if filters.get("item_code"):
        conditions.append("sle.item_code = %(item_code)s")
        params["item_code"] = filters["item_code"]

    if filters.get("warehouse"):
        conditions.append("sle.warehouse = %(warehouse)s")
        params["warehouse"] = filters["warehouse"]

    where_clause = " AND ".join(conditions)

    sql = f"""
        WITH latest_sle AS (
            SELECT
                sle.posting_date,
                sle.item_code,
                sle.warehouse,
                MAX(sle.posting_time) AS last_sle_time
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabItem` item 
                ON sle.item_code = item.name 
                AND item.is_stock_item = 1
            WHERE {where_clause}
            GROUP BY 
                sle.posting_date,
                sle.item_code,
                sle.warehouse
        ),

        latest_riv AS (
            SELECT
                riv.item_code,
                riv.warehouse,
                riv.posting_date,
                riv.posting_time AS last_riv_time,
                riv.name AS repost_item_valuation_id,
                riv.status
            FROM `tabRepost Item Valuation` riv
            INNER JOIN (
                SELECT
                    item_code,
                    warehouse,
                    posting_date,
                    MAX(posting_time) AS max_time
                FROM `tabRepost Item Valuation`
                WHERE based_on = 'Item and Warehouse'
                GROUP BY item_code, warehouse, posting_date
            ) latest
            ON riv.item_code = latest.item_code
            AND riv.warehouse = latest.warehouse
            AND riv.posting_date = latest.posting_date
            AND riv.posting_time = latest.max_time
            WHERE riv.based_on = 'Item and Warehouse'
        )

        SELECT
            sle.posting_date AS date,
            sle.item_code,
            sle.warehouse,

            CASE
                WHEN riv.last_riv_time IS NULL THEN NULL
                WHEN sle.last_sle_time > riv.last_riv_time THEN NULL
                ELSE riv.repost_item_valuation_id
            END AS repost_item_valuation_id,

            CASE
                WHEN riv.last_riv_time IS NULL THEN 'Remaining'
                WHEN sle.last_sle_time > riv.last_riv_time THEN 'Remaining'
                ELSE riv.status
            END AS status

        FROM latest_sle sle

        LEFT JOIN latest_riv riv
            ON sle.item_code = riv.item_code
            AND sle.warehouse = riv.warehouse
            AND sle.posting_date = riv.posting_date

        ORDER BY sle.posting_date DESC, sle.item_code, sle.warehouse
    """

    data = frappe.db.sql(sql, params, as_dict=True)

    status_filter = filters.get("repost_status")
    remaining_only = filters.get("remaining_repost")

    if status_filter and remaining_only:
        data = [d for d in data if d.get("status") == "Remaining"]

    elif status_filter:
        data = [d for d in data if d.get("status") == status_filter]

    elif remaining_only:
        data = [d for d in data if d.get("status") == "Remaining"]

    return data


import frappe
from frappe.utils import getdate, now, nowdate
from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import (
    execute_repost_item_valuation,
)



# !nissi.nissi.report.repost_item_valuation_report.repost_item_valuation_report.auto_repost_item_valuation

@frappe.whitelist()
def auto_repost_item_valuation(posting_date=None):
    """Auto create and submit Repost Item Valuation for all stock items of a posting date."""

    posting_date = posting_date or nowdate()

    # ---------------- SQL: Find items to repost ---------------- #
    sql = """
        WITH latest_sle AS (
            SELECT
                sle.posting_date,
                sle.item_code,
                sle.warehouse,
                MAX(sle.posting_time) AS last_sle_time
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabItem` item 
                ON sle.item_code = item.name 
                AND item.is_stock_item = 1
            WHERE sle.docstatus = 1
              AND sle.is_cancelled = 0
              AND sle.posting_date = %(posting_date)s
            GROUP BY sle.posting_date, sle.item_code, sle.warehouse
        ),

        latest_riv AS (
            SELECT
                riv.item_code,
                riv.warehouse,
                riv.posting_date,
                riv.posting_time AS last_riv_time,
                riv.name,
                riv.status
            FROM `tabRepost Item Valuation` riv
            INNER JOIN (
                SELECT
                    item_code,
                    warehouse,
                    posting_date,
                    MAX(posting_time) AS max_time
                FROM `tabRepost Item Valuation`
                WHERE based_on = 'Item and Warehouse'
                GROUP BY item_code, warehouse, posting_date
            ) latest
            ON riv.item_code = latest.item_code
            AND riv.warehouse = latest.warehouse
            AND riv.posting_date = latest.posting_date
            AND riv.posting_time = latest.max_time
            WHERE riv.based_on = 'Item and Warehouse'
        )

        SELECT DISTINCT
            sle.posting_date,
            sle.item_code,
            sle.warehouse
        FROM latest_sle sle

        LEFT JOIN latest_riv riv
            ON sle.item_code = riv.item_code
            AND sle.warehouse = riv.warehouse
            AND sle.posting_date = riv.posting_date

        WHERE
            riv.last_riv_time IS NULL
            OR sle.last_sle_time > riv.last_riv_time
            OR riv.status = 'Failed'
    """

    data = frappe.db.sql(sql, {"posting_date": posting_date}, as_dict=True)

    if not data:
        return []

    # ---------------- PROCESS ---------------- #
    success_list = []
    failed_list = []
    created_rivs = []

    seen = set()

    for d in data:
        key = (d["item_code"], d["warehouse"])
        if key in seen:
            continue
        seen.add(key)

        try:
            # CREATE AND SUBMIT RIV
            riv = frappe.new_doc("Repost Item Valuation")
            riv.based_on = "Item and Warehouse"
            riv.posting_date = posting_date
            riv.posting_time = now()
            riv.item_code = d["item_code"]
            riv.warehouse = d["warehouse"]

            riv.insert(ignore_permissions=True)
            riv.submit()

            created_rivs.append(riv.name)
            success_list.append(f"{riv.item_code} - {riv.warehouse}")

        except Exception:
            failed_list.append(
                {
                    "item_code": d["item_code"],
                    "warehouse": d["warehouse"],
                    "error": "Execution Exception",
                }
            )
            frappe.log_error(
                frappe.get_traceback(),
                f"Auto Repost Creation Failed: {d['item_code']} - {d['warehouse']}",
            )

    # ---------------- EXECUTE ALL RIVs ---------------- #
    if created_rivs:
        execute_repost_item_valuation()

    # ---------------- SUMMARY LOG ---------------- #
    total_records = len(seen)
    total_success = len(success_list)
    total_failed = len(failed_list)

    message = f"""
    <h3>Auto Repost Summary</h3>
    <b>Date:</b> {posting_date}<br>
    <b>Total Picked:</b> {total_records}<br>
    <b>Success:</b> {total_success}<br>
    <b>Failed:</b> {total_failed}<br><br>
    """

    if success_list:
        message += "<b>Success Items:</b><br><ul>"
        for s in success_list[:100]:
            message += f"<li>{s}</li>"
        if len(success_list) > 100:
            message += f"<li>... and {len(success_list) - 100} more</li>"
        message += "</ul><br>"

    if failed_list:
        message += "<b>Failed Items:</b><br><ul>"
        for f in failed_list[:100]:
            message += f"<li>{f['item_code']} - {f['warehouse']} : {f['error']}</li>"
        if len(failed_list) > 100:
            message += f"<li>... and {len(failed_list) - 100} more</li>"
        message += "</ul>"

    frappe.log_error(message, "Auto Repost Item Valuation Summary")

    return created_rivs





# WHEN WE WANT TO REPOST ALL THE PAST ENTRIES
@frappe.whitelist()
def auto_repost_item_valuation_for_all():
    """Auto create and submit Repost Item Valuation for all stock items of a posting date."""

    # ---------------- SQL: Find items to repost ---------------- #
    sql = """
        WITH latest_sle AS (
            SELECT
                sle.posting_date,
                sle.item_code,
                sle.warehouse,
                MAX(sle.posting_time) AS last_sle_time
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabItem` item 
                ON sle.item_code = item.name 
                AND item.is_stock_item = 1
            WHERE sle.docstatus = 1
              AND sle.is_cancelled = 0
            GROUP BY sle.posting_date, sle.item_code, sle.warehouse
        ),

        latest_riv AS (
            SELECT
                riv.item_code,
                riv.warehouse,
                riv.posting_date,
                riv.posting_time AS last_riv_time,
                riv.name,
                riv.status
            FROM `tabRepost Item Valuation` riv
            INNER JOIN (
                SELECT
                    item_code,
                    warehouse,
                    posting_date,
                    MAX(posting_time) AS max_time
                FROM `tabRepost Item Valuation`
                WHERE based_on = 'Item and Warehouse'
                GROUP BY item_code, warehouse, posting_date
            ) latest
            ON riv.item_code = latest.item_code
            AND riv.warehouse = latest.warehouse
            AND riv.posting_date = latest.posting_date
            AND riv.posting_time = latest.max_time
            WHERE riv.based_on = 'Item and Warehouse'
        )

        SELECT DISTINCT
            sle.posting_date,
            sle.item_code,
            sle.warehouse
        FROM latest_sle sle

        LEFT JOIN latest_riv riv
            ON sle.item_code = riv.item_code
            AND sle.warehouse = riv.warehouse
            AND sle.posting_date = riv.posting_date

        WHERE
            riv.last_riv_time IS NULL
            OR sle.last_sle_time > riv.last_riv_time
            OR riv.status = 'Failed'
    """

    data = frappe.db.sql(sql, as_dict=True)

    if not data:
        return []

    # ---------------- PROCESS ---------------- #
    success_list = []
    failed_list = []
    created_rivs = []

    seen = set()
    
    # AVOID DUPLICATES
    for d in data:
        key = (d["item_code"], d["warehouse"])
        if key in seen:
            continue
        seen.add(key)

        try:
            # CREATE AND SUBMIT RIV
            riv = frappe.new_doc("Repost Item Valuation")
            riv.based_on = "Item and Warehouse"
            riv.posting_date = getdate()
            riv.posting_time = now()
            riv.item_code = d["item_code"]
            riv.warehouse = d["warehouse"]

            riv.insert(ignore_permissions=True)
            riv.submit()

            created_rivs.append(riv.name)
            success_list.append(f"{riv.item_code} - {riv.warehouse}")

        except Exception:
            failed_list.append(
                {
                    "item_code": d["item_code"],
                    "warehouse": d["warehouse"],
                    "error": "Execution Exception",
                }
            )
            frappe.log_error(
                frappe.get_traceback(),
                f"Auto Repost Creation Failed: {d['item_code']} - {d['warehouse']}",
            )

    # ---------------- EXECUTE ALL RIVs ---------------- #
    if created_rivs:
        execute_repost_item_valuation()

    # ---------------- SUMMARY LOG ---------------- #
    total_records = len(seen)
    total_success = len(success_list)
    total_failed = len(failed_list)

    message = f"""
    <h3>Auto Repost Summary</h3>
    <b>Date:</b> {getdate()}<br>
    <b>Total Picked:</b> {total_records}<br>
    <b>Success:</b> {total_success}<br>
    <b>Failed:</b> {total_failed}<br><br>
    """

    if success_list:
        message += "<b>Success Items:</b><br><ul>"
        for s in success_list[:100]:
            message += f"<li>{s}</li>"
        if len(success_list) > 100:
            message += f"<li>... and {len(success_list) - 100} more</li>"
        message += "</ul><br>"

    if failed_list:
        message += "<b>Failed Items:</b><br><ul>"
        for f in failed_list[:100]:
            message += f"<li>{f['item_code']} - {f['warehouse']} : {f['error']}</li>"
        if len(failed_list) > 100:
            message += f"<li>... and {len(failed_list) - 100} more</li>"
        message += "</ul>"

    frappe.log_error(message, "Auto Repost Item Valuation Summary")

    return created_rivs
