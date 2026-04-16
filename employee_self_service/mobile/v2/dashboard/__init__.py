import frappe
from employee_self_service.mobile.v2.dashboard.utils import *

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
