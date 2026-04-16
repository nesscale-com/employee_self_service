import frappe
from frappe import _
from frappe.utils import *
from employee_self_service.mobile.v2.api_utils import *
from erpnext.accounts.utils import get_fiscal_year


def get_leave_balance_report_old(employee, company, fiscal_year):
    fiscal_year = get_fiscal_year(fiscal_year=fiscal_year, as_dict=True)
    year_start_date = get_date_str(fiscal_year.get("year_start_date"))
    # year_end_date = get_date_str(fiscal_year.get("year_end_date"))
    filters_leave_balance = {
        "from_date": year_start_date,
        "to_date": add_days(today(), 1),
        "company": company,
        "employee": employee,
    }
    from frappe.desk.query_report import run

    return run("Employee Leave Balance", filters=filters_leave_balance)["result"]


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


def get_latest_leave(dashboard_data, employee):
    leave_applications = frappe.get_all(
        "Leave Application",
        filters={"employee": employee},
        fields=[
            "status",
            "DATE_FORMAT(from_date, '%d-%m-%Y') AS from_date",
            "DATE_FORMAT(to_date, '%d-%m-%Y') AS to_date",
            "name",
            "leave_type",
            "description",
        ],
        order_by="modified desc",
    )
    if len(leave_applications) >= 1:
        dashboard_data["latest_leave"] = leave_applications[0]
