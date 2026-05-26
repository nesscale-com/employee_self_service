from calendar import monthrange

import frappe
from erpnext.setup.doctype.employee.employee import (
    get_holiday_list_for_employee,
)
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, today

from employee_self_service.mobile.v1.api_utils import (
    convert_timezone,
    ess_validate,
    exception_handler,
    gen_response,
    get_employee_by_user,
    get_system_timezone,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_attendance_list_by_date(date=None):
    try:
        if not date:
            return gen_response(500, "date is required", [])

        emp_data = get_employee_by_user(frappe.session.user)
        employee_name = emp_data.get("name")

        # Fetch attendance records
        attendance_list = frappe.get_all(
            "Attendance",
            filters={
                "employee": employee_name,
                "attendance_date": date,
                "docstatus": 1,
            },
            fields=[
                "name",
                "DATE_FORMAT(attendance_date, '%d %W') AS attendance_date",
                "status",
                "working_hours",
                "in_time",
                "out_time",
                "late_entry",
            ],
        )

        if not attendance_list:
            return gen_response(500, "no attendance found for this year and month", [])

        # Get user and system time zones
        user_time_zone = frappe.db.get_value("User", frappe.session.user, "time_zone")
        system_timezone = get_system_timezone()
        to_convert_timezone = user_time_zone != system_timezone

        # Get all related check-ins in one query to minimize DB calls
        attendance_names = [att["name"] for att in attendance_list]
        checkins = frappe.get_all(
            "Employee Checkin",
            filters={"attendance": ["in", attendance_names]},
            fields=["attendance", "log_type", "time", "location", "log_location"],
        )

        # Create a mapping for check-ins
        checkin_map = {}
        for checkin in checkins:
            checkin_time = (
                convert_timezone(
                    checkin["time"], system_timezone, user_time_zone
                ).strftime("%I:%M %p")
                if to_convert_timezone
                else checkin["time"].strftime("%I:%M %p")
            )
            checkin_map.setdefault(checkin["attendance"], []).append(
                {
                    "log_type": checkin["log_type"],
                    "time": checkin_time,
                    "location": checkin.get("location"),
                    "log_location": checkin.get("log_location"),
                }
            )

        # Process attendance records
        for attendance in attendance_list:
            if to_convert_timezone:
                if attendance["in_time"]:
                    attendance["in_time"] = convert_timezone(
                        attendance["in_time"], system_timezone, user_time_zone
                    ).strftime("%I:%M %p")
                if attendance["out_time"]:
                    attendance["out_time"] = convert_timezone(
                        attendance["out_time"], system_timezone, user_time_zone
                    ).strftime("%I:%M %p")
            else:
                attendance["in_time"] = (
                    attendance["in_time"].strftime("%I:%M %p")
                    if attendance["in_time"]
                    else None
                )
                attendance["out_time"] = (
                    attendance["out_time"].strftime("%I:%M %p")
                    if attendance["out_time"]
                    else None
                )

            attendance["employee_checkin_detail"] = checkin_map.get(
                attendance["name"], []
            )

            # Remove unnecessary fields
            attendance.pop("name", None)
            attendance.pop("status", None)
            attendance.pop("late_entry", None)
        return gen_response(
            200, "Attendance data retrieved successfully", attendance_list
        )
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_ess_calendar_details(year=None, month=None):
    """
    API to fetch attendance details for a given employee, year, and month.

    :param year: Year (YYYY)
    :param month: Month (MM)
    :return: JSON response with day-wise attendance status
    """
    try:
        year, month = cint(year), cint(month)
        days_in_month = monthrange(year, month)[1]
        month_start_date = f"{year}-{month:02d}-01"
        month_end_date = f"{year}-{month:02d}-{days_in_month}"

        # Get Employee Details
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "image", "department", "company"]
        )
        if not emp_data:
            return gen_response(404, "Employee not found")

        # Get Attendance and Holiday Data
        attendance_records = get_attendance_records(
            emp_data["name"], month_start_date, month_end_date
        )
        holidays = get_employee_holidays(
            emp_data["name"], month_start_date, month_end_date
        )

        # Prepare Response Data
        attendance_data = build_attendance_data(
            year, month, days_in_month, attendance_records, holidays
        )
        return gen_response(
            200, "ESS calendar data fetched successfully", attendance_data
        )

    except Exception as e:
        return exception_handler(e)


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


def _get_attendance_summary(employee, year, month):
    """
    Compute present/absent/days-off counts for a given month using the same
    data sources as get_ess_calendar_details (attendance records + holiday list).

    Returns a dict in the same shape as get_attendance_details in ess.py.
    """
    days_in_month = monthrange(year, month)[1]
    month_start = getdate(f"{year}-{month:02d}-01")
    month_end = getdate(f"{year}-{month:02d}-{days_in_month}")
    yesterday = getdate(add_days(today(), -1))

    if yesterday < month_start:
        till_date_days = 0
    elif yesterday > month_end:
        till_date_days = days_in_month
    else:
        till_date_days = date_diff(yesterday, month_start) + 1

    present_count = flt(0)
    leave_count = flt(0)
    holidays_till_date = flt(0)

    if till_date_days > 0:
        till_date = min(yesterday, month_end)

        attendance_records = get_attendance_records(
            employee,
            month_start.strftime("%Y-%m-%d"),
            month_end.strftime("%Y-%m-%d"),
        )
        holidays = get_employee_holidays(
            employee,
            month_start.strftime("%Y-%m-%d"),
            month_end.strftime("%Y-%m-%d"),
        )

        for record in attendance_records:
            record_date = getdate(record["attendance_date"])
            if record_date > till_date:
                continue
            status = record["status"]
            if status in ("Present", "Work From Home"):
                present_count += 1
            elif status == "Half Day":
                present_count += 0.5
                leave_count += 0.5
            elif status == "On Leave":
                leave_count += 1

        holidays_till_date = flt(sum(1 for h in holidays if h <= till_date))

    days_off = leave_count + holidays_till_date
    absent = max(flt(0), flt(till_date_days) - present_count - days_off)

    return {
        "month_title": month_start.strftime("%B"),
        "data": [
            {"type": "Total Days", "data": [till_date_days, days_in_month]},
            {"type": "Presents", "data": [present_count, till_date_days]},
            {"type": "Absents", "data": [absent, till_date_days]},
            {"type": "Days off", "data": [days_off, till_date_days]},
        ],
    }


@frappe.whitelist()
def get_attendance_details_dashboard():
    """Current-month attendance summary for the dashboard."""
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["name", "company"])
        if not emp_data:
            return gen_response(404, "Employee not found")
        today_date = getdate(today())
        summary = _get_attendance_summary(emp_data["name"], today_date.year, today_date.month)
        return gen_response(200, "Attendance data get successfully", summary)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_attendance_details_by_month(year=None, month=None):
    """Attendance summary for a given year and month."""
    try:
        if not year or not month:
            return gen_response(500, "year and month are required")

        year, month = cint(year), cint(month)
        today_date = getdate(today())
        if (year, month) > (today_date.year, today_date.month):
            return gen_response(400, "Cannot fetch attendance for a future month")

        emp_data = get_employee_by_user(frappe.session.user, fields=["name", "company"])
        if not emp_data:
            return gen_response(404, "Employee not found")
        summary = _get_attendance_summary(emp_data["name"], year, month)
        return gen_response(200, "Attendance data get successfully", summary)
    except Exception as e:
        return exception_handler(e)