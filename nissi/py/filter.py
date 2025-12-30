import frappe

@frappe.whitelist()
def get_all_child_accounts(doctype, txt, searchfield, start, page_len, filters):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    acc_type = filters.get("type")
    company = filters.get("company")

    abbr = frappe.db.get_value("Company", company, "abbr")

    # ------------------------
    # DEBIT → Expense accounts
    # ------------------------
    if acc_type == "Debit":
        return frappe.db.sql("""
            SELECT name
            FROM `tabAccount`
            WHERE root_type = 'Expense'
              AND company = %s
              AND name LIKE %s
            ORDER BY name
            LIMIT %s, %s
        """, (company, f"%{txt}%", start, page_len))

    # ------------------------
    # CREDIT → Petty Cash children
    # ------------------------
    elif acc_type == "Credit":
        parent_account = f"PETTY CASH - {abbr}"

        return frappe.db.sql("""
            SELECT name
            FROM `tabAccount`
            WHERE parent_account = %s
              AND company = %s
              AND name LIKE %s
            ORDER BY name
            LIMIT %s, %s
        """, (parent_account, company, f"%{txt}%", start, page_len))

    return []
