import frappe

# from frappe.utils import pretty_date, getdate, fmt_money
from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
    get_employee_by_user,
    validate_employee_data
)
from erpnext.accounts.utils import get_fiscal_year

from frappe.utils import (
    getdate,
    nowdate,
    today,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_leave_application_list():
    """
    Get Leave Application which is already applied. Get Leave Balance Report
    """
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        validate_employee_data(emp_data)
        leave_application_fields = [
            "name",
            "leave_type",
            "DATE_FORMAT(from_date, '%d-%m-%Y') as from_date",
            "DATE_FORMAT(to_date, '%d-%m-%Y') as to_date",
            "total_leave_days",
            "description",
            "status",
            "DATE_FORMAT(posting_date, '%d-%m-%Y') as posting_date",
            "half_day",
            "DATE_FORMAT(half_day_date, '%d-%m-%Y') as half_day_date",
        ]
        pending_leaves = frappe.get_all(
            "Leave Application",
            filters={"employee": emp_data.get("name"), "status": "Open"},
            fields=leave_application_fields,
        )

        history_leaves = frappe.get_all(
            "Leave Application",
            fields=leave_application_fields,
            filters=[["Leave Application","status","not in",["Open"]], ["Leave Application","employee","=",emp_data.get("name")]],
        )
        
        fiscal_year = get_fiscal_year(nowdate())[0]
        if not fiscal_year:
            return gen_response(500, "Fiscal year not set")
        res = get_leave_balance_report(
            emp_data.get("name"), emp_data.get("company"), fiscal_year
        )
        leave_applications = {
            "pending": pending_leaves,
            "history": history_leaves,
            "balance": res,
        }
        return gen_response(200, "Leave data getting successfully", leave_applications)
    except Exception as e:
        return exception_handler(e)
    

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