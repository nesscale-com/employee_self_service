import frappe
from frappe import _
from frappe.utils import *
from employee_self_service.mobile.v1.api_utils import *

def get_month_year_details(expense):
    date = getdate(expense.get("posting_date"))
    month = date.strftime("%B")
    year = date.year
    return f"{month} {year}"

def get_salary_slip_details(ss_id):
    return frappe.get_doc("Salary Slip", ss_id)

def update_shift_last_sync(emp_data):
    if emp_data.get("default_shift"):
        frappe.db.set_value(
            "Shift Type",
            emp_data.get("default_shift"),
            "last_sync_of_checkin",
            now_datetime(),
        )
