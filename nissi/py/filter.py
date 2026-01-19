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
        accounts = frappe.get_list(
            "Account",
            fields=["name"],
            filters={
                "root_type": "Expense",
                "company": company,
                "name": ["like", f"%{txt}%"]
            },
            start=start,
            page_length=page_len,
            ignore_permissions=False   
        )
        return [(d.name,) for d in accounts]

    # ------------------------
    # CREDIT → Petty Cash children
    # ------------------------
    elif acc_type == "Credit":
        user = frappe.session.user
        account_assignment = frappe.get_all(
            "Petty Cash Account Assignment",
            filters={"user": user},fields=["account"])
        if account_assignment:
            return [(d.account,) for d in account_assignment]

    return []

