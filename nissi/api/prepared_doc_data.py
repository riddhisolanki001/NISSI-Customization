import frappe
import re
import json
import gzip
from frappe.utils.file_manager import get_file_path


@frappe.whitelist()
def get_general_ledger_prepared_data():
    """
    Returns parsed data + applied filter values from the latest Prepared Report 
    for General Ledger.
    
    FEATURES:
        - Detects gzip and plain JSON storage
        - Adds mode_of_payment field for Payment Entry rows
        - Maps 'Voucher Subtype' to 'narration' field
        - Ensures doc_name equals voucher_no for all voucher types
    
    UPDATED FIELDS:
        - narration: Set to Voucher Subtype value
        - doc_name: Payment Entry record name (for Payment Entry rows)
        - mode_of_payment: Payment method from Payment Entry
        - cheque_no: Reference number for non-withholding entries
    """
    try:
        # Step 1: Get latest Prepared Report for General Ledger
        pr = frappe.get_all(
            "Prepared Report",
            filters={"report_name": "General Ledger"},
            fields=["name", "filters"], 
            order_by="creation desc",
            limit=1
        )

        if not pr:
            return {
                "success": False, 
                "message": "No Prepared Report found for General Ledger"
            }

        pr = pr[0]
        prepared_report_name = pr.name

        # Parse filters JSON (may be empty)
        applied_filters = frappe.parse_json(pr.filters) if pr.filters else {}

        # Step 2: Get latest attached output file
        file_doc = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Prepared Report",
                "attached_to_name": prepared_report_name
            },
            fields=["file_url"],
            order_by="creation desc",
            limit=1
        )

        if not file_doc:
            return {
                "success": False, 
                "message": "No report file found (maybe still generating?)"
            }

        file_path = get_file_path(file_doc[0].file_url)

        # Step 3: Load JSON content (gzip aware)
        try:
            with gzip.open(file_path, "rb") as gz:
                raw = gz.read().decode("utf-8")
            content = json.loads(raw)
        except OSError:
            with open(file_path, "r") as f:
                content = json.load(f)

        data = content.get("result", []) or content.get("data", [])

        # Safely extract required boundary values
        first_row = data[0] if len(data) > 0 else None
        last_row = data[-1] if len(data) > 0 else None
        second_last_row = data[-2] if len(data) > 1 else None
        
        # Remove boundary rows (opening, total, closing)
        cleaned_data = data.copy()  
        if len(cleaned_data) > 0:
            cleaned_data.pop(0)  # Remove opening row
        if len(cleaned_data) > 0:
            cleaned_data.pop(-1)  # Remove closing row
        if len(cleaned_data) > 1:
            cleaned_data.pop(-1)  # Remove total row
            
        # Step 4: Enrich data with additional fields
        payment_cache = {}
        withholding_cache = {}
        mode_of_payment_cache = {}

        for row in cleaned_data:
            # Get voucher_type and voucher_no
            voucher_type = row.get("voucher_type")
            voucher_no = row.get("voucher_no")
            
            # IMPORTANT: Set narration to Voucher Subtype
            voucher_subtype = row.get("voucher_subtype")
            row["narration"] = voucher_subtype
            
            # Set doc_name to voucher_no for all rows with voucher information
            if voucher_no:
                row["doc_name"] = voucher_no

            # Special handling for Payment Entry rows
            if voucher_type == "Payment Entry" and voucher_no:
                pe_name = voucher_no
                account_name = (row.get("account") or "").lower()
                against_account = (row.get("against") or "").lower()

                # Fetch mode_of_payment (cache to avoid repeated DB calls)
                if pe_name not in mode_of_payment_cache:
                    mode_of_payment = frappe.db.get_value(
                        "Payment Entry",
                        pe_name,
                        "mode_of_payment"
                    )
                    mode_of_payment_cache[pe_name] = mode_of_payment

                row["mode_of_payment"] = mode_of_payment_cache.get(pe_name) or ""

                # Withholding Tax handling for Supplier payments
                if row.get("party_type") == "Supplier" and (
                    "withholding" in account_name or "withholding" in against_account
                ):
                    if pe_name not in withholding_cache:
                        tax_category = frappe.db.get_value(
                            "Payment Entry",
                            pe_name,
                            "tax_withholding_category"
                        )
                        withholding_cache[pe_name] = tax_category

                    tax_category = withholding_cache.get(pe_name)

                    if tax_category:
                        # Extract percentage from tax category
                        match = re.search(r"(\d+(\.\d+)?)\s*%", tax_category)
                        if match:
                            percentage = match.group(1)
                            row["narration"] = f"Withholding Tax-{percentage}%"

                    row["cheque_no"] = None

                # Non-withholding Payment Entry rows
                else:
                    if pe_name not in payment_cache:
                        payment_cache[pe_name] = frappe.db.get_value(
                            "Payment Entry",
                            pe_name,
                            "reference_no"
                        )

                    row["cheque_no"] = payment_cache.get(pe_name)

        return {
            "success": True,
            "prepared_report": prepared_report_name,
            "applied_filters": applied_filters,
            "data": cleaned_data,
            "balance_details": {
                "opening": first_row,
                "total": second_last_row,
                "closing": last_row
            }
        }
    
    except Exception as e:
        frappe.log_error(
            "get_general_ledger_prepared_data",
            frappe.get_traceback()
        )
        return {
            "success": False,
            "message": "Error processing General Ledger data",
            "error": str(e)
        }