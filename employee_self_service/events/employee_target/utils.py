import frappe
from frappe import _


def get_employee_from_sales_team(doctype, docname):
    sales_persons = frappe.get_all(
        "Sales Team",
        filters={"parenttype": doctype, "parent": docname},
        fields=["sales_person"],
    )
    employees = []
    for sp in sales_persons:
        emp = frappe.db.get_value("Sales Person", sp.sales_person, "employee")
        if emp:
            employees.append(emp)
    return employees


def handle_groupwise_target(doc, target_doc, employee, metric, selector):
    """Handle Item Group / Customer Group based target logs"""

    scrubbed_selector = frappe.scrub(selector)

    # Get selected groups from target entry
    target_groups = [
        d.get(scrubbed_selector)
        for d in target_doc.get(f"{scrubbed_selector}_wise_target")
    ]
    expanded_groups = get_group_hierarchy(selector, target_groups)

    if selector == "Item Group":
        for item in doc.get("items"):
            if item.item_group in expanded_groups:
                create_target_log(
                    employee=employee,
                    doc=doc,
                    target_doc=target_doc,
                    metric=metric,
                    group_field="item_group",
                    group_value=item.item_group,
                    amount=item.amount,
                    qty=item.qty,
                )
    elif selector == "Customer Group":
        customer_group = doc.customer_group
        if not customer_group:
            return

        if customer_group in expanded_groups:
            create_target_log(
                employee=employee,
                doc=doc,
                target_doc=target_doc,
                metric=metric,
                group_field="customer_group",
                group_value=customer_group,
                amount=doc.total,
                qty=doc.total_qty,
            )


def get_group_hierarchy(selector, target_groups):
    """Expand groups by including their children"""

    scrubbed_selector = frappe.scrub(selector)
    all_groups = frappe.get_all(
        selector, fields=["name", f"parent_{scrubbed_selector}", "is_group"]
    )
    parent_field = f"parent_{scrubbed_selector}"
    final_groups = set(target_groups)

    for group in target_groups:
        for g in all_groups:
            if g.name == group or g.get(parent_field) == group:
                final_groups.add(g.name)
    return final_groups


def create_target_log(
    employee,
    doc,
    target_doc,
    metric,
    group_field=None,
    group_value=None,
    amount=0,
    qty=0,
):
    """Create and submit SP Target Log"""
    log_data = {
        "doctype": "SP Target Log",
        "employee": employee,
        "customer": doc.get("customer"),
        "date": frappe.utils.nowdate(),
        "employee_target_entry": target_doc.name,
        "reference_doctype": doc.doctype,
        "reference_docname": doc.name,
        "amount": amount if metric == "Value" else 0,
        "qty": qty if metric == "Quantity" else 0,
    }
    if group_field and group_value:
        log_data[group_field] = group_value

    target_log = frappe.get_doc(log_data)
    target_log.insert(ignore_permissions=True)
    target_log.submit()


def target_setting():
    return frappe.db.get_single_value("ESS Target Settings", "enable_target_management")
