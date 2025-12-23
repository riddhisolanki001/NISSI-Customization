import frappe

@frappe.whitelist()
def get_all_child_accounts(doctype, txt, searchfield, start, page_len, filters):
    # filters comes as dict (or JSON string)
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    acc_type = filters.get("type")
    company = filters.get("company")

    abbr = frappe.db.get_value("Company", company, "abbr")

    if acc_type == "Debit":
        parent_account = f"EXPENSES - {abbr}"

        parent = frappe.get_value(
            "Account",
            parent_account,
            ["lft", "rgt"],
            as_dict=True
        )
        if not parent:
            return []

        return frappe.db.sql("""
            SELECT name
            FROM `tabAccount`
            WHERE lft > %s AND rgt < %s
              AND is_group = 0
              AND name LIKE %s
            ORDER BY name
            LIMIT %s, %s
        """, (parent.lft, parent.rgt, f"%{txt}%", start, page_len))

    elif acc_type == "Credit":
        return frappe.db.sql("""
            SELECT name
            FROM `tabAccount`
            WHERE name = %s
              AND name LIKE %s
            LIMIT %s, %s
        """, (f"PETTY CASH - {abbr}", f"%{txt}%", start, page_len))

    return []
