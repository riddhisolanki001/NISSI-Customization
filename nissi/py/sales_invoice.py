import frappe
from frappe.utils import flt, cint, add_days, today
import nissi

def collect_all_negative_stock_errors(doc,method):
    if not doc.update_stock:
        return

    shortage = []

    for row in doc.items:

        if not row.item_code or not row.warehouse:
            continue

        item = frappe.get_doc("Item", row.item_code)
        row_no = row.idx

        # =======================================================
        # NORMAL ITEM (No batch, No serial)
        # =======================================================
        if not item.has_batch_no and not item.has_serial_no:
            actual = frappe.db.get_value(
                "Bin",
                {"item_code": row.item_code, "warehouse": row.warehouse},
                "actual_qty"
            ) or 0

            if flt(actual) < flt(row.qty):
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b>: Required <b>{row.qty}</b>, Available <b>{actual}</b> in <b>{row.warehouse}</b>"
                )

        # =======================================================
        # BATCH ITEM ONLY
        # =======================================================
        if item.has_batch_no and not item.has_serial_no:

            from erpnext.stock.doctype.batch.batch import get_batch_qty

            total_batch_qty = 0

            # If batch selected
            if row.batch_no:
                total_batch_qty = get_batch_qty(
                    batch_no=row.batch_no,
                    item_code=row.item_code,
                    warehouse=row.warehouse,
                ) or 0

                if flt(total_batch_qty) < flt(row.qty):
                    shortage.append(
                        f"Row {row_no} – <b>{row.item_code}</b> (Batch {row.batch_no}): Required <b>{row.qty}</b>, Available <b>{total_batch_qty}</b>"
                    )
            else:
                # Sum all batches
                batches = frappe.get_all("Batch", filters={"item": row.item_code}, fields=["name"])
                for b in batches:
                    qty = get_batch_qty(
                        batch_no=b.name,
                        item_code=row.item_code,
                        warehouse=row.warehouse,
                    ) or 0
                    total_batch_qty += qty

                if flt(total_batch_qty) < flt(row.qty):
                    shortage.append(
                        f"Row {row_no} – <b>{row.item_code}</b> (Batch Item): Required <b>{row.qty}</b>, Available <b>{total_batch_qty}</b> across batches"
                    )

        # =======================================================
        # SERIAL ITEM ONLY
        # =======================================================
        if item.has_serial_no and not item.has_batch_no:

            # Count available serials in warehouse
            serial_count = frappe.db.count(
                "Serial No",
                {
                    "item_code": row.item_code,
                    "warehouse": row.warehouse,
                    "status": "Active",
                }
            )

            if serial_count < flt(row.qty):
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b> (Serial): Required <b>{row.qty}</b>, Available <b>{serial_count}</b>"
                )

            # ------------------------------------------
            # Validate user-selected serials
            # ------------------------------------------
            if row.serial_no:

                serial_list = [s.strip() for s in row.serial_no.split("\n") if s.strip()]

                # Count mismatch
                if len(serial_list) != int(row.qty):
                    shortage.append(
                        f"Row {row_no} – <b>{row.item_code}</b>: Selected <b>{len(serial_list)}</b> serials but Qty = <b>{row.qty}</b>"
                    )

                #  Check if all serial numbers exist
                existing_serials = frappe.db.get_all(
                    "Serial No",
                    filters={"name": ["in", serial_list]},
                    pluck="name"
                )

                missing = set(serial_list) - set(existing_serials)
                if missing:
                    shortage.append(
                        f"Row {row_no} – <b>{row.item_code}</b>: Serial(s) do not exist: <b>{', '.join(missing)}</b>"
                    )

                # Check serials in wrong warehouse
                wrong_wh = frappe.db.get_all(
                    "Serial No",
                    filters={
                        "name": ["in", serial_list],
                        "warehouse": ["!=", row.warehouse]
                    },
                    fields=["name", "warehouse"]
                )

                if wrong_wh:
                    wrong_list = ", ".join([s["name"] for s in wrong_wh])
                    shortage.append(
                        f"Row {row_no} – <b>{row.item_code}</b>: Serial(s) <b>{wrong_list}</b> not in warehouse <b>{row.warehouse}</b>"
                    )


        # =======================================================
        # SERIAL + BATCH VALIDATION (MERGED & CORRECTED)
        # =======================================================
        if item.has_batch_no and item.has_serial_no:

            # -----------------------------------
            # Mandatory field checks
            # -----------------------------------
            if not row.batch_no:
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b>: Batch No is required but missing"
                )

            if not row.serial_no:
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b>: Serial No is required but missing"
                )

            # If either missing, skip detailed validation
            if not row.batch_no or not row.serial_no:
                continue

            # -----------------------------------
            # Count batch qty using Serial No (NOT SLE)
            # -----------------------------------
            batch_available = frappe.db.count(
                "Serial No",
                {
                    "item_code": row.item_code,
                    "warehouse": row.warehouse,
                    "batch_no": row.batch_no,
                    "status": "Active"
                }
            )

            if flt(batch_available) < flt(row.qty):
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b>: Batch <b>{row.batch_no}</b> has only <b>{batch_available}</b> but requires <b>{row.qty}</b>"
                )

            # -----------------------------------
            # Parse serial list
            # -----------------------------------
            serial_list = [s.strip() for s in row.serial_no.split("\n") if s.strip()]

            # Serial count mismatch
            if len(serial_list) != int(row.qty):
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b>: Selected <b>{len(serial_list)}</b> serials but Qty = <b>{row.qty}</b>"
                )

            # -----------------------------------
            # Serial existence check
            # -----------------------------------
            existing_serials = frappe.db.get_all(
                "Serial No",
                filters={"name": ["in", serial_list]},
                pluck="name"
            )

            missing = set(serial_list) - set(existing_serials)
            if missing:
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b>: Serial(s) do not exist: <b>{', '.join(missing)}</b>"
                )

            # -----------------------------------
            # Validate Serial → Batch mapping
            # -----------------------------------
            wrong_batch = frappe.db.get_all(
                "Serial No",
                filters={
                    "name": ["in", serial_list],
                    "batch_no": ["!=", row.batch_no]
                },
                pluck="name"
            )

            if wrong_batch:
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b>: Serial(s) <b>{', '.join(wrong_batch)}</b> not linked with Batch <b>{row.batch_no}</b>"
                )

            # -----------------------------------
            # Validate Serial → Warehouse mapping
            # -----------------------------------
            wrong_wh = frappe.db.get_all(
                "Serial No",
                filters={
                    "name": ["in", serial_list],
                    "warehouse": ["!=", row.warehouse]
                },
                pluck="name"
            )

            if wrong_wh:
                shortage.append(
                    f"Row {row_no} – <b>{row.item_code}</b>: Serial(s) <b>{', '.join(wrong_wh)}</b> not in Warehouse <b>{row.warehouse}</b>"
                )

    # =======================================================
    # THROW ALL ERRORS TOGETHER
    # =======================================================
    if shortage:
        msg = "<br>".join(shortage)
        frappe.throw(
            f"{msg}",
            title="Insufficient Stock"
        )


def check_credit_limit_on_validate(doc, method):
    if doc.is_return:
        return

    from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding

    credit_limit = get_credit_limit(doc.customer, doc.company)
    if not credit_limit:
        return

    credit_controller_role = frappe.db.get_single_value("Accounts Settings", "credit_controller")
    if credit_controller_role and credit_controller_role in frappe.get_roles():
        return

    bypass_credit_limit_check_at_sales_order = frappe.db.get_value(
        "Customer Credit Limit",
        filters={"parent": doc.customer, "parenttype": "Customer", "company": doc.company},
        fieldname="bypass_credit_limit_check",
    )

    customer_outstanding = get_customer_outstanding(
        doc.customer, doc.company, bypass_credit_limit_check_at_sales_order
    )
    customer_outstanding += flt(doc.grand_total)

    if flt(customer_outstanding) > flt(credit_limit):
        frappe.msgprint(
            frappe._(
                "Credit limit has been crossed for customer {0} ({1}/{2}).<br><br>"
                "Please contact your supervisor to extend the credit limits for {0}."
            ).format(doc.customer, customer_outstanding, credit_limit),
            title=frappe._("Credit Limit Crossed"),
            raise_exception=1,
        )


def check_credit_days_overdue(doc, method):
    if doc.is_return:
        return

    credit_days = frappe.db.get_value(
        "Customer Credit Limit",
        {"parent": doc.customer, "parenttype": "Customer", "company": doc.company},
        "custom_credit_days",
    )
    if not credit_days:
        return

    credit_controller_role = frappe.db.get_single_value("Accounts Settings", "credit_controller")
    if credit_controller_role and credit_controller_role in frappe.get_roles():
        return

    cutoff_date = add_days(today(), -cint(credit_days))

    overdue = frappe.db.sql(
        """
        SELECT name, posting_date, outstanding_amount
        FROM `tabSales Invoice`
        WHERE customer = %s
          AND company = %s
          AND docstatus = 1
          AND outstanding_amount > 0
          AND posting_date < %s
          AND name != %s
        """,
        (doc.customer, doc.company, cutoff_date, doc.name),
        as_dict=True,
    )

    if overdue:
        rows = "".join(
            "<li>{name} &mdash; Posted: {posting_date}, Outstanding: {outstanding_amount}</li>".format(**inv)
            for inv in overdue
        )
        frappe.throw(
            frappe._(
                "Customer {0} has unpaid invoice(s) beyond the "
                "{1}-day credit period:<ul>{2}</ul>"
            ).format(doc.customer, credit_days, rows),
            title=frappe._("Credit Days Exceeded"),
        )
