import frappe

@frappe.whitelist()
def repost_ple_for_voucher(voucher_type, voucher_no):
    doc = frappe.new_doc("Repost Accounting Ledger")

    doc.append("vouchers", {
        "voucher_type": voucher_type,
        "voucher_no": voucher_no
    })

    doc.insert(ignore_permissions=True)
    doc.submit()
    frappe.db.commit()



@frappe.whitelist()
def check_account_against_latest_bank_gl(doctype, docname, account):
    """
    Returns:
        True  -> if latest Bank GL account != account
        False -> if matches or not found
    """
    if not (doctype and docname and account):
        return False

    gl_entries = frappe.get_all(
        "GL Entry",
        filters={
            "voucher_type": doctype,
            "voucher_no": docname,
            "is_cancelled": 0
        },
        fields=["name", "account", "posting_date", "creation"],
        order_by="posting_date desc, creation desc",
        limit=10
    )

    if not gl_entries:
        return False

    for gl in gl_entries:
        account_type = frappe.db.get_value("Account", gl.account, "account_type")
        if account_type == "Bank":
            if gl.account == account:
                return False   
            else:
                return True    

   
    return False


