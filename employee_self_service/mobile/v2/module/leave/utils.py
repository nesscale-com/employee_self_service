import frappe
from frappe import _ 
from frappe.utils import getdate

def get_leave_balance_report(employee, company, fiscal_year):
    """
    Returns a map of leave type and balance details like:
    {
    'Casual Leave': {'allocated_leaves': 10.0, 'balance_leaves': 5.0},
    'Earned Leave': {'allocated_leaves': 3.0, 'balance_leaves': 3.0},
    }
    """
    from hrms.hr.doctype.leave_application.leave_application import get_leave_details

    date = getdate()
    leave_balance = []

    leave_details = get_leave_details(employee, date)
    allocation = leave_details["leave_allocation"]

    for leave_type, details in allocation.items():
        leave_balance.append(
            {
                "leave_type": leave_type,
                "total_leaves": details.get("total_leaves"),
                "leaves_allocated": details.get("remaining_leaves"),
                "leaves_taken": details.get("leaves_taken"),
                "expired_leaves": details.get("expired_leaves"),
                "employee": employee,
                "closing_balance": details.get("remaining_leaves"),
            }
        )

    return leave_balance
