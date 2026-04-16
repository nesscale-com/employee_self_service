import frappe
from frappe import _
from erpnext.setup.doctype.employee.employee import (
    get_holiday_list_for_employee,
)
from frappe.utils import *

def get_attendance_records(employee, start_date, end_date):
    """Fetch attendance records for a given employee and date range."""
    return frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [start_date, end_date]],
            "docstatus": 1,
        },
        fields=["attendance_date", "status"],
    )


def get_employee_holidays(employee, start_date, end_date):
    """Fetch holiday dates for a given employee and date range."""
    holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)

    if not holiday_list:
        return set()

    holiday_dates = frappe.get_all(
        "Holiday",
        filters={
            "parent": holiday_list,
            "holiday_date": ["between", [start_date, end_date]],
        },
        fields=["holiday_date"],
    )
    return {getdate(h["holiday_date"]) for h in holiday_dates}


def build_attendance_data(year, month, days_in_month, attendance_records, holidays):
    """Build the final attendance data structure."""
    attendance_data = {}

    # Populate Attendance records
    for record in attendance_records:
        date_str = getdate(record["attendance_date"]).strftime("%Y-%m-%d")
        status = record["status"]
        attendance_data[date_str] = "Absent" if status == "On Leave" else status

    # Populate Holidays and Other Days
    for day in range(1, days_in_month + 1):
        date = getdate(f"{year}-{month:02d}-{day}")
        date_str = date.strftime("%Y-%m-%d")

        if date_str not in attendance_data:
            attendance_data[date_str] = "Holiday" if date in holidays else "No Record"

    return attendance_data

