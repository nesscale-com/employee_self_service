import frappe
from frappe import _
from .utils import (
    get_employee_from_sales_team, 
    get_active_target_entries,
    handle_item_group_target,
    handle_customer_group_target,
    handle_combined_target,
    create_target_log,
    target_setting
)
from frappe.utils import getdate


def create_sales_person_target_log(doc, method=None):
    """
    Create target logs for employees based on Sales Order/Sales Invoice submission.
    
    Processes employee targets by identifying sales team members, finding their active
    target entries, and creating appropriate target logs based on document metrics.
    Supports value-based, item group-based, and customer group-based target tracking.
    """
    enable_target = target_setting()
    if not enable_target:
        return

    employees = get_employee_from_sales_team(doc.doctype, doc.name)
    if not employees:
        return

    # Extract transaction date for target validation
    transaction_date = doc.get("posting_date") or doc.get("transaction_date")
    if not transaction_date:
        frappe.log_error(
            title="Missing Transaction Date",
            message=f"No transaction date found in {doc.doctype} {doc.name}"
        )
        return
    
    transaction_date = getdate(transaction_date)

    for employee in employees:
        try:
            # Find target entries that are active for the transaction date
            active_targets = get_active_target_entries(employee, doc.doctype, transaction_date)
            
            if not active_targets:
                continue

            for target_doc in active_targets:
                metric = target_doc.get("metric")
                selector = target_doc.get("selector")

                # Check if both item group and customer group targets are configured
                has_item_groups = target_doc.get("item_group_wise_target")
                has_customer_groups = target_doc.get("customer_group_wise_target")

                if selector == "Item Group" or (has_item_groups and not has_customer_groups):
                    # Handle item group only targeting
                    handle_item_group_target(doc, target_doc, employee, metric, transaction_date)
                elif selector == "Customer Group" or (has_customer_groups and not has_item_groups):
                    # Handle customer group only targeting
                    handle_customer_group_target(doc, target_doc, employee, metric, transaction_date)
                else:
                    # Process general value or quantity-based targets
                    create_target_log(
                        employee=employee,
                        doc=doc,
                        target_doc=target_doc,
                        metric=metric,
                        amount=doc.total,
                        qty=doc.total_qty,
                        transaction_date=transaction_date,
                    )
                    
        except Exception as e:
            frappe.log_error(
                title="Target Log Processing Failed",
                message=frappe.get_traceback()
            )


def reverse_sales_person_target_log(doc, method=None):
    enable_target = target_setting()
    if not enable_target:
        return

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
