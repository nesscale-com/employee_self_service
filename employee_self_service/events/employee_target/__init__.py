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
        selector = target_doc.get("selector")

        if selector in ["Item Group", "Customer Group"]:
            handle_groupwise_target(doc, target_doc, employee, metric, selector)
        else:
            create_target_log(
                employee=employee,
                doc=doc,
                target_doc=target_doc,
                metric=metric,
                amount=doc.total,
                qty=doc.total_qty,
            )


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
