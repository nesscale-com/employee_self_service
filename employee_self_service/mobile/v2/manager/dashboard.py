import frappe
from frappe.utils import today

from employee_self_service.mobile.v2.api_utils import *


def _employee_sets_today(emp_list):
    if not emp_list:
        return set(), set(), set(), set()

    start = f"{today()} 00:00:00"
    end = f"{today()} 23:59:59"

    in_set = set(
        frappe.get_all(
            "Employee Checkin",
            filters={
                "time": ["between", [start, end]],
                "employee": ["in", emp_list],
                "log_type": "IN",
            },
            pluck="employee",
        )
    )

    out_set = set(
        frappe.get_all(
            "Employee Checkin",
            filters={
                "time": ["between", [start, end]],
                "employee": ["in", emp_list],
                "log_type": "OUT",
            },
            pluck="employee",
        )
    )

    leave_set = set(
        frappe.get_all(
            "Leave Application",
            filters={
                "status": "Approved",
                "docstatus": 1,
                "from_date": ["<=", today()],
                "to_date": [">=", today()],
                "employee": ["in", emp_list],
            },
            pluck="employee",
        )
    )

    not_in_set = set(emp_list) - in_set - leave_set - out_set
    return in_set, out_set, leave_set, not_in_set


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard():
    try:
        emp_data = get_employee_by_user(
            frappe.session.user,
            fields=["name", "company", "image", "employee_name", "gender"],
        )
        notice_board = get_notice_board(emp_data.get("name"))
        # attendance_details = get_attendance_details(emp_data)
        log_details = get_last_log_details(emp_data.get("name"))
        settings = get_ess_settings()
        dashboard_data = {
            "notice_board": notice_board,
            "leave_balance": [],
            "latest_leave": {},
            "latest_expense": {},
            "latest_salary_slip": {},
            "stop_location_validate": settings.get("location_validate"),
            "last_log_type": log_details.get("log_type"),
            "version": settings.get("version") or "1.0",
            "update_version_forcefully": settings.get("update_version_forcefully") or 1,
            "company": emp_data.get("company") or "Employee Dashboard",
            "last_log_time": (
                log_details.get("time").strftime("%I:%M %p")
                if log_details.get("time")
                else ""
            ),
            "check_in_with_image": settings.get("check_in_with_image"),
            "check_in_with_location": settings.get("check_in_with_location"),
            "quick_task": settings.get("quick_task"),
            "allow_odometer_reading_input": settings.get(
                "allow_odometer_reading_input"
            ),
            "gender": emp_data.get("gender"),
            "capture_location_for_quotation": settings.get(
                "capture_location_for_quotation"
            ),
            "capture_location_for_sales_order": settings.get(
                "capture_location_for_sales_order"
            ),
            "out_of_location_checkout": settings.get("out_of_location_checkout"),
            "enable_project_and_task_in_expense_claim": settings.get(
                "enable_project_and_task_in_expense_claim"
            ),
            "notification_count": frappe.db.count(
                "ESS Notification Log", {"recipient": frappe.session.user, "read": 0}
            ),
            "role_based_menu_visibility": settings.get(
                "enable_role_based_menu_visibility"
            ),
            "enable_todo": settings.get("enable_todo"),
            "enable_modular_menu": settings.get("enable_modular_menu"),
        }
        # "approval_requests": get_workflow_documents(internal=True)
        dashboard_data["employee_image"] = emp_data.get("image")
        dashboard_data["employee_name"] = emp_data.get("employee_name")
        get_latest_expense(dashboard_data, emp_data.get("name"))
        get_latest_ss(dashboard_data, emp_data.get("name"))
        get_last_log_type(dashboard_data, emp_data.get("name"))
        return gen_response(200, "Dashboard data get successfully", dashboard_data)

    except Exception as e:
        return exception_handler(e)


def get_last_log_details(employee):
    log_details = frappe.db.sql(
        """SELECT log_type,
        time
        FROM `tabEmployee Checkin`
        WHERE employee=%s
        AND DATE(time)=%s
        ORDER BY time DESC""",
        (employee, today()),
        as_dict=1,
    )

    if log_details:
        user_time_zone = frappe.db.get_value("User", frappe.session.user, "time_zone")
        system_timezone = get_system_timezone()
        if user_time_zone:
            log_details[0].time = convert_timezone(
                log_details[0].time, system_timezone, user_time_zone
            )
        if log_details[0].log_type == "IN":
            in_logs = [log for log in log_details if log["log_type"] == "IN"]
            if user_time_zone:
                in_logs[-1].time = convert_timezone(
                    in_logs[-1].time, system_timezone, user_time_zone
                )
            first_check_in = in_logs[-1]
            return first_check_in
        return log_details[0]
    else:
        return {"log_type": "OUT", "time": None}


def get_latest_expense(dashboard_data, employee):
    global_defaults = get_global_defaults()

    latest_expense = frappe.get_all(
        "Expense Claim",
        filters={"employee": employee},
        fields=["name", "approval_status"],
        order_by="modified desc",
        limit_page_length=1,
    )

    if not latest_expense:
        return  # Exit early if no expense claims exist

    expense_doc = frappe.get_doc("Expense Claim", latest_expense[0].name)
    if not expense_doc.expenses:
        return  # Exit if there are no expenses

    first_expense = expense_doc.expenses[0]  # Directly access the first row

    dashboard_data["latest_expense"] = {
        "status": expense_doc.approval_status,
        "date": first_expense.expense_date.strftime("%d-%m-%Y"),
        "expense_type": first_expense.expense_type,
        "description": first_expense.description,
        "amount": fmt_money(
            expense_doc.total_claimed_amount,
            currency=global_defaults.get("default_currency"),
        ),
        "name": expense_doc.name,
        "total_expenses": len(expense_doc.expenses),
    }


def get_latest_ss(dashboard_data, employee):
    global_defaults = get_global_defaults()
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={"employee": employee},
        fields=["*"],
        order_by="modified desc",
    )
    if len(salary_slips) >= 1:
        month_year = get_month_year_details(salary_slips[0])
        dashboard_data["latest_salary_slip"] = dict(
            name=salary_slips[0].name,
            month_year=month_year,
            posting_date=salary_slips[0].posting_date.strftime("%d-%m-%Y"),
            # amount=salary_slips[0].gross_pay,
            amount=fmt_money(
                salary_slips[0].gross_pay,
                currency=global_defaults.get("default_currency"),
            ),
            total_working_days=salary_slips[0].total_working_days,
        )


def get_last_log_type(dashboard_data, employee):
    logs = frappe.get_all(
        "Employee Checkin",
        filters={"employee": employee},
        fields=["log_type"],
        order_by="time desc",
    )

    if len(logs) >= 1:
        dashboard_data["last_log_type"] = logs[0].log_type


def get_notice_board(employee=None):
    filters = [
        ["Notice Board Employee", "employee", "=", employee],
        ["Notice Board", "apply_for", "=", "Specific Employees"],
        ["Notice Board", "from_date", "<=", today()],
        ["Notice Board", "to_date", ">=", today()],
    ]
    notice_board_employee = frappe.get_all(
        "Notice Board",
        filters=filters,
        fields=["notice_title as title", "message"],
    )
    common_filters = [
        ["Notice Board", "apply_for", "=", "All Employee"],
        ["Notice Board", "from_date", "<=", today()],
        ["Notice Board", "to_date", ">=", today()],
    ]
    notice_board_common = frappe.get_all(
        "Notice Board",
        filters=common_filters,
        fields=["notice_title as title", "message"],
    )
    notice_board_employee.extend(notice_board_common)
    return notice_board_employee


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats():
    try:
        stats = {
            "total_employees": 0,
            "clock_in": 0,
            "clock_out": 0,
            "on_leave": 0,
            "not_clock_in": 0,
            "approval": 0,
            "tasks": 0,
        }

        # permitted active employees
        emp_list = (
            frappe.get_list("Employee", filters={"status": "Active"}, pluck="name")
            or []
        )
        stats["total_employees"] = len(emp_list)

        in_set, out_set, leave_set, not_in_set = _employee_sets_today(emp_list)

        stats["clock_in"] = len(in_set)
        stats["clock_out"] = len(out_set)
        stats["on_leave"] = len(leave_set)
        stats["not_clock_in"] = len(not_in_set)

        return gen_response(200, "Stats retrieved successfully", stats)
    except Exception as e:
        return exception_handler(e)


# type must be one of: clock_in, clock_out, on_leave, not_clock_in
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats_list(type):
    try:
        kind = (type or "").strip().lower()
        if kind not in {"clock_in", "clock_out", "on_leave", "not_clock_in"}:
            return gen_response(
                400,
                "Invalid type",
                {"allowed": ["clock_in", "clock_out", "on_leave", "not_clock_in"]},
            )

        emp_list = (
            frappe.get_list("Employee", filters={"status": "Active"}, pluck="name")
            or []
        )
        if not emp_list:
            return gen_response(200, "No employees", [])

        in_set, out_set, leave_set, not_in_set = _employee_sets_today(emp_list)
        bucket = {
            "clock_in": in_set,
            "clock_out": out_set,
            "on_leave": leave_set,
            "not_clock_in": not_in_set,
        }[kind]

        if not bucket:
            return gen_response(200, "No records", [])

        # fetch display info once
        rows = frappe.get_all(
            "Employee",
            filters={"name": ["in", list(bucket)]},
            fields=["name", "employee_name", "image", "gender"],
        )
        data = [
            {
                "employee": r.name,
                "name": r.employee_name or r.name,
                "image": r.image or "",
                "gender": r.gender,
            }
            for r in rows
        ]

        # optional: keep UI stable by name ordering (simple)
        data.sort(key=lambda x: x["name"].lower())

        return gen_response(200, "Stats fetched successfully", data)
    except Exception as e:
        return exception_handler(e)
