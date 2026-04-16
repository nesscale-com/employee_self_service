from calendar import monthrange
import frappe
from frappe import _
from frappe.utils import *
from employee_self_service.mobile.v2.attendance.utils import *
from employee_self_service.mobile.v2.api_utils import *

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
                "attendance_date",
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
            attendance["attendance_date"] = ( attendance["attendance_date"].strftime("%d %A") if attendance["attendance_date"] else None )

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

@frappe.whitelist()
def get_attendance_details_dashboard():
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["name", "company"])
        attendance_details = get_attendance_details(emp_data)
        return gen_response(
            200, "Leave balance data get successfully", attendance_details
        )
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
def run_attendance_report(employee, company):
    filters = {
        "filter_based_on": "Month",
        "month": cstr(frappe.utils.getdate().month),
        "year": cstr(frappe.utils.getdate().year),
        "company": company,
        "employee": employee,
        "summarized_view": 1,
    }
    from frappe.desk.query_report import run

    attendance_report = run("Monthly Attendance Sheet", filters=filters)
    if attendance_report.get("result"):
        return attendance_report.get("result")[0]

def get_attendance_details(emp_data, year=None, month=None):
    last_date = get_last_day(today())
    first_date = get_first_day(today())
    total_days = date_diff(last_date, first_date) + 1
    till_date_days = date_diff(today(), first_date) + 1
    days_off = 0
    absent = 0
    total_present = 0
    attendance_report = run_attendance_report(
        emp_data.get("name"), emp_data.get("company")
    )
    holidays = get_till_date_holiday_month_wise(emp_data, first_date, today())
    if attendance_report:
        days_off = flt(attendance_report.get("total_leaves")) + flt(holidays)
        absent = till_date_days - (
            flt(days_off) + flt(attendance_report.get("total_present"))
        )
        total_present = attendance_report.get("total_present")
    attendance_details = {
        "month_title": f"{frappe.utils.getdate().strftime('%B')}",
        "data": [
            {
                "type": "Total Days",
                "data": [
                    till_date_days,
                    total_days,
                ],
            },
            {
                "type": "Presents",
                "data": [
                    total_present,
                    till_date_days,
                ],
            },
            {
                "type": "Absents",
                "data": [
                    absent,
                    till_date_days,
                ],
            },
            {
                "type": "Days off",
                "data": [
                    days_off,
                    till_date_days,
                ],
            },
        ],
    }
    return attendance_details

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_attendance_list(year=None, month=None):
    try:
        if not year or not month:
            return gen_response(500, "year and month is required", [])
        emp_data = get_employee_by_user(frappe.session.user)
        present_count = 0
        absent_count = 0
        late_count = 0

        employee_attendance_list = frappe.get_all(
            "Attendance",
            filters={
                "employee": emp_data.get("name"),
                "attendance_date": [
                    "between",
                    [
                        f"{int(year)}-{int(month)}-01",
                        f"{int(year)}-{int(month)}-{calendar.monthrange(int(year), int(month))[1]}",
                    ],
                ],
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

        if not employee_attendance_list:
            return gen_response(500, "no attendance found for this year and month", [])

        user_time_zone = frappe.db.get_value("User", frappe.session.user, "time_zone")
        system_timezone = get_system_timezone()
        to_convert_timezone = False
        if user_time_zone != system_timezone:
            to_convert_timezone = True
        for attendance in employee_attendance_list:
            employee_checkin_details = []
            if to_convert_timezone:
                if attendance["in_time"]:
                    attendance["in_time"] = convert_timezone(
                        attendance["in_time"], system_timezone, user_time_zone
                    ).strftime("%I:%M %p")
                if attendance["out_time"]:
                    attendance["out_time"] = convert_timezone(
                        attendance["out_time"], system_timezone, user_time_zone
                    ).strftime("%I:%M %p")
                employee_checkin_details = frappe.get_all(
                    "Employee Checkin",
                    filters={"attendance": attendance.get("name")},
                    fields=["log_type", "time"],
                )
                for employee_checkin in employee_checkin_details:
                    employee_checkin["time"] = convert_timezone(
                        employee_checkin["time"], system_timezone, user_time_zone
                    ).strftime("%I:%M %p")
            else:
                employee_checkin_details = frappe.get_all(
                    "Employee Checkin",
                    filters={"attendance": attendance.get("name")},
                    fields=["log_type", "time_format(time, '%h:%i%p') as time"],
                )

            attendance["employee_checkin_detail"] = employee_checkin_details

            if attendance["status"] == "Present":
                present_count += 1

                if attendance["late_entry"] == 1:
                    late_count += 1

            elif attendance["status"] == "Absent":
                absent_count += 1

            del attendance["name"]
            del attendance["status"]
            del attendance["late_entry"]

        attendance_details = {
            "days_in_month": calendar.monthrange(int(year), int(month))[1],
            "present": present_count,
            "absent": absent_count,
            "late": late_count,
        }
        attendance_data = {
            "attendance_details": attendance_details,
            "attendance_list": employee_attendance_list,
        }
        return gen_response(
            200, "Attendance data getting successfully", attendance_data
        )

    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_attendance_list_by_date(date=None):
    try:
        if not date:
            return gen_response(500, "year and month is required", [])
        emp_data = get_employee_by_user(frappe.session.user)

        employee_attendance_list = frappe.get_all(
            "Attendance",
            filters={
                "employee": emp_data.get("name"),
                "attendance_date": ["=", date],
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

        if not employee_attendance_list:
            return gen_response(500, "no attendance found for this year and month", [])

        user_time_zone = frappe.db.get_value("User", frappe.session.user, "time_zone")
        system_timezone = get_system_timezone()
        to_convert_timezone = False
        if user_time_zone != system_timezone:
            to_convert_timezone = True
        for attendance in employee_attendance_list:
            employee_checkin_details = []
            if to_convert_timezone:
                if attendance["in_time"]:
                    attendance["in_time"] = convert_timezone(
                        attendance["in_time"], system_timezone, user_time_zone
                    ).strftime("%I:%M %p")
                if attendance["out_time"]:
                    attendance["out_time"] = convert_timezone(
                        attendance["out_time"], system_timezone, user_time_zone
                    ).strftime("%I:%M %p")
                employee_checkin_details = frappe.get_all(
                    "Employee Checkin",
                    filters={"attendance": attendance.get("name")},
                    fields=["log_type", "time"],
                )
                for employee_checkin in employee_checkin_details:
                    employee_checkin["time"] = convert_timezone(
                        employee_checkin["time"], system_timezone, user_time_zone
                    ).strftime("%I:%M %p")
            else:
                attendance["in_time"] = (
                    attendance["in_time"].strftime("%I:%M %p")
                    if attendance["in_time"]
                    else attendance["in_time"]
                )
                attendance["out_time"] = (
                    attendance["out_time"].strftime("%I:%M %p")
                    if attendance["out_time"]
                    else attendance["out_time"]
                )
                employee_checkin_details = frappe.get_all(
                    "Employee Checkin",
                    filters={"attendance": attendance.get("name")},
                    fields=[
                        "log_type",
                        "time_format(time, '%h:%i%p') as time",
                        "location",
                    ],
                )

            attendance["employee_checkin_detail"] = employee_checkin_details

            # if attendance["status"] == "Present":
            # present_count += 1

            # if attendance["late_entry"] == 1:
            #     late_count += 1

            # elif attendance["status"] == "Absent":
            #     absent_count += 1

            del attendance["name"]
            del attendance["status"]
            del attendance["late_entry"]

        return gen_response(
            200, "Attendance data getting successfully", employee_attendance_list
        )

    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
def get_attendance_details_by_month(year, month):
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["name", "company"])
        attendance_details = get_attendance_details(emp_data, year, month)
        return gen_response(
            200, "Leave balance data get successfully", attendance_details
        )
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_attendance_request(*args, **kwargs):
    required_fields = ["company", "from_date", "to_date", "reason"]
    data = {
        field: kwargs.get(field)
        for field in required_fields
        + ["half_day", "include_holidays", "shift", "explanation"]
    }
    missing_fields = [field for field in required_fields if not data[field]]

    if missing_fields:
        return gen_response(
            500,
            f"Please provide the following fields to proceed: {', '.join(missing_fields)}.",
        )

    try:
        employee = frappe.get_value(
            "Employee", {"user_id": frappe.session.user}, "name"
        )
        if not employee:
            return gen_response(500, "Employee record not found.")

        if kwargs.get("request_id"):
            request_doc = frappe.get_doc("Attendance Request", kwargs.get("request_id"))
            if request_doc.employee != employee:
                return gen_response(403, "Attendance request not found")

            request_doc.update(data)
            request_doc.save()
            return gen_response(200, "Attendance Request updated successfully.")

        request_doc = frappe.get_doc(
            {"doctype": "Attendance Request", "employee": employee, **data}
        )
        request_doc.insert(ignore_permissions=True)
        return gen_response(200, "Attendance Request created successfully.")

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to manage attendance requests.")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_shift_list():
    try:
        shift_type_list = frappe.get_list("Shift Type", fields=["name"])
        gen_response(200, "Shift Type list get successfully", shift_type_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for shift")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_attendance_request_list(**data):
    try:
        employee = frappe.get_value(
            "Employee", {"user_id": frappe.session.user}, "name"
        )
        if not employee:
            return gen_response(500, "Employee record not found.")

        filters = [["Attendance Request", "employee", "=", employee]]
        if data.get("filters"):
            filters.extend(data.get("filters"))

        attendance_request_list = frappe.get_all(
            "Attendance Request",
            filters=filters,
            fields=[
                "name",
                "employee",
                "employee_name",
                "department",
                "company",
                "from_date",
                "to_date",
                "half_day",
                "half_day_date",
                "include_holidays",
                "shift",
                "reason",
                "explanation",
            ],
        )

        for request in attendance_request_list:
            if request.get("from_date"):
                request["from_date"] = getdate(request["from_date"]).strftime(
                    "%d-%m-%Y"
                )
            if request.get("to_date"):
                request["to_date"] = getdate(request["to_date"]).strftime("%d-%m-%Y")

        return gen_response(
            200,
            "Attendance Request list retrieved successfully.",
            attendance_request_list,
        )
    except frappe.PermissionError as e:
        return gen_response(500, str(e))
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_attendance_request(request_id=None):
    if not request_id:
        return gen_response(500, "Request ID cannot be blank.")

    try:
        employee = frappe.get_value(
            "Employee", {"user_id": frappe.session.user}, "name"
        )
        if not employee:
            return gen_response(500, "Employee record not found.")

        if not frappe.db.exists(
            "Attendance Request", {"name": request_id, "employee": employee}
        ):
            return gen_response(500, "Attendance Request Not found")

        request_doc = frappe.get_value(
            "Attendance Request",
            {"name": request_id, "employee": employee},
            [
                "name",
                "employee",
                "employee_name",
                "department",
                "company",
                "from_date",
                "to_date",
                "half_day",
                "half_day_date",
                "include_holidays",
                "shift",
                "reason",
                "explanation",
            ],
            as_dict=True,
        )
        if request_doc.get("from_date"):
            request_doc["from_date"] = getdate(request_doc["from_date"]).strftime(
                "%d-%m-%Y"
            )
        if request_doc.get("to_date"):
            request_doc["to_date"] = getdate(request_doc["to_date"]).strftime(
                "%d-%m-%Y"
            )
        gen_response(200, "Attendance Request details get successfully.", request_doc)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to access attendance request")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def delete_attendance_request(request_id=None):
    if not request_id:
        return gen_response(500, "Request ID cannot be blank.")
    try:
        frappe.delete_doc("Attendance Request", request_id, force=1)
        return gen_response(200, "Attendance Request deleted successfully.")
    except frappe.PermissionError as e:
        return gen_response(500, str(e))
    except Exception as e:
        return exception_handler(e)
