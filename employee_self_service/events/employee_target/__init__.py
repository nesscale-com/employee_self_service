import frappe
from frappe import _
from .utils import *
from frappe.utils import getdate


def create_sales_person_target_log(doc, method=None):
    employees = get_employee_from_sales_team(doc.doctype, doc.name)
    if not employees:
        return

    for employee in employees:
        target_list = frappe.get_all(
            "Employee Target Entry",
            {"employee": employee, "target_module": doc.doctype},
            ["name"],
        )
        if not target_list:
            continue

        target_doc = frappe.get_doc("Employee Target Entry", target_list[0].name)
        transaction_date = doc.get("posting_date") or doc.get("transaction_date")
        if transaction_date:
            transaction_date = getdate(transaction_date)
            start_date = getdate(target_doc.start_date)
            end_date = getdate(target_doc.end_date)
            if not (start_date <= transaction_date <= end_date):
                continue

        metric = target_doc.get("metric")
        if target_doc.get("selector") == "Item Group":
            item_groups = [
                d.item_group for d in target_doc.get("item_group_wise_target")
            ]
            for item in doc.get("items"):
                if item.item_group in item_groups:
                    target_log = frappe.get_doc(
                        {
                            "doctype": "SP Target Log",
                            "employee": employee,
                            "customer": doc.get("customer"),
                            "date": frappe.utils.nowdate(),
                            "employee_target_entry": target_doc.name,
                            "reference_doctype": doc.doctype,
                            "reference_docname": doc.name,
                            "item_group": item.item_group,
                            "amount": item.amount if metric == "Value" else 0,
                            "qty": item.qty if metric == "Quantity" else 0,
                        }
                    )
                    target_log.insert(ignore_permissions=True)
                    target_log.submit()

        else:
            target_log = frappe.get_doc(
                {
                    "doctype": "SP Target Log",
                    "employee": employee,
                    "customer": doc.get("customer"),
                    "date": frappe.utils.nowdate(),
                    "employee_target_entry": target_doc.name,
                    "reference_doctype": doc.doctype,
                    "reference_docname": doc.name,
                    "amount": doc.total if metric == "Value" else 0,
                    "qty": doc.total_qty if metric == "Quantity" else 0,
                }
            )
            target_log.insert(ignore_permissions=True)
            target_log.submit()


def reverse_sales_person_target_log(doc, method=None):
    logs = frappe.get_all(
        "SP Target Log",
        filters={"reference_doctype": doc.doctype, "reference_docname": doc.name},
        pluck="name",
    )

    for log_name in logs:
        log_doc = frappe.get_doc("SP Target Log", log_name)
        if log_doc.docstatus == 1:
            log_doc.cancel()
        else:
            log_doc.delete(ignore_permissions=True)
