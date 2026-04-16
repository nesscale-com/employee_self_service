import calendar
import os
import frappe
from frappe import _
from frappe.handler import upload_file
from frappe.utils import *
from employee_self_service.employee_self_service.doctype.push_notification.push_notification import (
    create_push_notification,
)
from employee_self_service.mobile.v1.api_utils import *
from employee_self_service.mobile.v1.task import *
from employee_self_service.mobile.v1.transactions import *

# import apis from other modules due to mobile api versioning
from employee_self_service.mobile.v1.auth import *
from employee_self_service.mobile.v1.leave import *
from employee_self_service.mobile.v1.expense import get_expense_type,get_payable_account,book_expense
from employee_self_service.mobile.v1.attendance import (
    get_attendance_details_dashboard,
    run_attendance_report,
    get_attendance_details,
    get_attendance_list,
    get_attendance_list_by_date,
    get_attendance_details_by_month
)
from employee_self_service.mobile.v1.employee import *
from employee_self_service.mobile.v1.payment import get_transactions_old
from employee_self_service.mobile.v1.commen import *
from employee_self_service.mobile.v1.task import create_quick_task, get_quick_task_list
from employee_self_service.mobile.v1.notification import *

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

# def get_latest_expense(dashboard_data, employee):
#     global_defaults = get_global_defaults()
#     expense_list = frappe.get_all(
#         "Expense Claim",
#         filters={"employee": employee},
#         fields=["name"],
#         order_by="modified desc",
#     )
#     if len(expense_list) >= 1:
#         expense_doc = frappe.get_doc("Expense Claim", expense_list[0].name)
#         for row in expense_doc.expenses:
#             dashboard_data["latest_expense"] = dict(
#                 status=expense_doc.approval_status,
#                 date=row.expense_date.strftime("%d-%m-%Y"),
#                 expense_type=row.expense_type,
#                 description=row.description,
#                 # amount=expense_doc.expenses[0].amount,
#                 amount=fmt_money(
#                     row.amount,
#                     currency=global_defaults.get("default_currency"),
#                 ),
#                 name=expense_doc.name,
#             )

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

def daily_notice_board_event():
    create_employee_birthday_board("birthday")
    create_employee_birthday_board("work_anniversary")

def create_employee_birthday_board(event_type):
    event_type_map = {"work_anniversary": "Work Anniversary", "birthday": "Birthday"}
    title, message = frappe.db.get_value(
        "Notice Board Template",
        {"notice_board_template_type": event_type_map.get(event_type)},
        ["board_title", "message"],
    )
    if title and message:
        emp_today_birthdays = get_employees_having_an_event_today(event_type)
        for emp in emp_today_birthdays:
            frappe.get_doc(
                doctype="Notice Board",
                notice_title=title,
                message=message,
                from_date=today(),
                to_date=today(),
                apply_for="Specific Employees",
                employees=[dict(employee=emp.get("emp_id"))],
            ).insert(ignore_permissions=True)


def get_employees_having_an_event_today(event_type, date=None):
    if event_type == "birthday":
        condition_column = "date_of_birth"
    elif event_type == "work_anniversary":
        condition_column = "date_of_joining"
    else:
        return

    employees_born_today = frappe.db.multisql(
        {
            "mariadb": f"""
            SELECT `name` as 'emp_id',`personal_email`, `company`, `company_email`, `user_id`, `employee_name` AS 'name', `image`, `date_of_joining`
            FROM `tabEmployee`
            WHERE
                DAY({condition_column}) = DAY(%(today)s)
            AND
                MONTH({condition_column}) = MONTH(%(today)s)
            AND
                `status` = 'Active'
        """,
            "postgres": f"""
            SELECT "name" AS 'emp_id',"personal_email", "company", "company_email", "user_id", "employee_name" AS 'name', "image"
            FROM "tabEmployee"
            WHERE
                DATE_PART('day', {condition_column}) = date_part('day', %(today)s)
            AND
                DATE_PART('month', {condition_column}) = date_part('month', %(today)s)
            AND
                "status" = 'Active'
        """,
        },
        dict(today=getdate(date), condition_column=condition_column),
        as_dict=1,
    )
    return employees_born_today

def leave_application_list(date=None):
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        validate_employee_data(emp_data)
        leave_application_fields = [
            "name",
            "leave_type",
            "from_date",
            "to_date",
            "total_leave_days",
            "description",
            "status",
            "posting_date",
        ]

        filters = {"employee": emp_data.get("name")}

        if date:
            date = getdate(date)
            filters["from_date"] = ["<=", date]
            filters["to_date"] = [">=", date]

        upcoming_leaves = frappe.get_all(
            "Leave Application",
            filters=filters,
            fields=leave_application_fields,
        )

        leave_applications = {"upcoming": upcoming_leaves}

        return leave_applications
    except Exception as e:
        return exception_handler(e)


def notice_board_list(employee=None, date=None):
    filters = [
        ["Notice Board Employee", "employee", "=", employee],
        ["Notice Board", "apply_for", "=", "Specific Employees"],
        ["Notice Board", "from_date", "<=", getdate(date)],
        ["Notice Board", "to_date", ">=", getdate(date)],
    ]
    notice_board_employee = frappe.get_all(
        "Notice Board",
        filters=filters,
        fields=["notice_title as title", "message as description"],
    )
    common_filters = [
        ["Notice Board", "apply_for", "=", "All Employee"],
        ["Notice Board", "from_date", "<=", getdate(date)],
        ["Notice Board", "to_date", ">=", getdate(date)],
    ]
    notice_board_common = frappe.get_all(
        "Notice Board",
        filters=common_filters,
        fields=["notice_title as title", "message as description"],
    )
    notice_board_employee.extend(notice_board_common)
    return notice_board_employee


def holiday_list(date=None):
    emp_data = get_employee_by_user(frappe.session.user)
    from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

    holiday_list = get_holiday_list_for_employee(emp_data.name, raise_exception=False)

    filters = [
        ["Holiday", "holiday_date", "=", getdate(date)],
        ["Holiday", "parent", "=", holiday_list],
    ]

    holidays = frappe.get_all(
        "Holiday", filters=filters, fields=["'holiday' as title", "description"]
    )

    return holidays


@frappe.whitelist()
@ess_validate(methods=["GET"])
def upcoming_activity(date=None):
    try:
        if not date:
            return gen_response(500, "date is required", [])

        leaves = leave_application_list(date=date)

        upcoming_data = {date: []}

        for leave in leaves["upcoming"]:
            upcoming_data[date].append(
                {"title": leave.get("name"), "description": leave.get("leave_type")}
            )

        notice_board = notice_board_list(
            get_employee_by_user(frappe.session.user).get("name"), date=date
        )
        if notice_board:
            upcoming_data[date].extend(notice_board)

        birthday = get_employees_having_an_event_today("birthday", date=date)
        for birthdate in birthday:
            upcoming_data[date].append(
                {
                    "title": f"{birthdate.get('name')}'s Birthday",
                    "description": birthdate.get("name"),
                    "image": birthdate.get("image"),
                }
            )

        work_anniversary = get_employees_having_an_event_today(
            "work_anniversary", date=date
        )
        for anniversary in work_anniversary:
            upcoming_data[date].append(
                {
                    "title": f"{anniversary.get('name')}'s work anniversary",
                    "description": anniversary.get("name"),
                    "image": anniversary.get("image"),
                }
            )
        holidays = holiday_list(date=date)
        if holidays:
            upcoming_data[date].extend(holidays)

        return gen_response(200, "Upcoming activity details", upcoming_data)

    except Exception as e:
        return exception_handler(e)

def send_notification_on_event():
    birthday_events = get_employees_having_an_event_today("birthday", date=today())
    for event in birthday_events:
        create_push_notification(
            title=f"{event.get('name')}'s Birthday",
            message=f"Wish happy birthday to {event['name']}",
            send_for="All User",
            notification_type="event",
        )

    anniversary_events = get_employees_having_an_event_today(
        "work_anniversary", date=today()
    )
    for anniversary in anniversary_events:
        create_push_notification(
            title=f"{anniversary.get('name')}' s Work Anniversary",
            message=f"Wish work anniversary {anniversary['name']}",
            send_for="All User",
            notification_type="event",
        )


def global_holiday_list(date=None):
    global_company = frappe.db.get_single_value("Global Defaults", "default_company")
    employee_holiday_list = frappe.get_all(
        "Employee",
        {"company": global_company, "holiday_list": ("!=", "")},
        ["employee", "holiday_list", "user_id"],
    )
    holidays = []
    for employee in employee_holiday_list:
        filters = [
            ["Holiday", "holiday_date", "=", getdate(date)],
            ["Holiday", "parent", "=", employee.holiday_list],
        ]
        holidays_list = frappe.get_all(
            "Holiday", filters=filters, fields=["'holiday' as title", "description"]
        )
        for holiday in holidays_list:
            holiday["user_id"] = employee.user_id
            holidays.append(holiday)
    return holidays


def on_holiday_event():
    holiday_list = global_holiday_list(date=today())
    for holiday in holiday_list:
        create_push_notification(
            title=f"{holiday.get('title')}",
            message=f"{holiday.get('description')}",
            send_for="Single User",
            user=holiday.get("user_id"),
            notification_type="Holiday",
        )

def on_leave_application_update(doc, event):
    user = frappe.get_value("Employee", {"name": doc.employee}, "user_id")
    leave_approver = frappe.get_value(
        "Employee", {"prefered_email": doc.leave_approver}, "employee_name"
    )

    if doc.status == "Approved":
        create_push_notification(
            title=f"{doc.name} is Approved",
            message=f"{leave_approver} accept your leave request",
            send_for="Single User",
            user=user,
            notification_type="leave_application",
        )

    elif doc.status == "Rejected":
        create_push_notification(
            title=f"{doc.name} is Rejected",
            message=f"{leave_approver} reject your leave request",
            send_for="Single User",
            user=user,
            notification_type="leave_application",
        )


def on_expense_submit(doc, event):
    user = frappe.get_value("Employee", {"name": doc.employee}, "user_id")
    expense_approver = frappe.get_value(
        "Employee", {"prefered_email": doc.expense_approver}, "employee_name"
    )
    if doc.approval_status == "Approved":
        create_push_notification(
            title=f"{doc.name} is Approved",
            message=f"{expense_approver} accept your expense claim request",
            send_for="Single User",
            user=user,
            notification_type="expense_claim",
        )

    elif doc.approval_status == "Rejected":
        create_push_notification(
            title=f"{doc.name} is Rejected",
            message=f"{expense_approver} reject your expense claim request",
            send_for="Single User",
            user=user,
            notification_type="expense_claim",
        )


# moved to expense.py
@frappe.whitelist()
@ess_validate(methods=["POST"])
def apply_expense():
    try:
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "company", "expense_approver"]
        )

        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)

        payable_account = get_payable_account(emp_data.get("company"))
        expense_doc = frappe.get_doc(
            doctype="Expense Claim",
            employee=emp_data.name,
            expense_approver=emp_data.expense_approver,
            expenses=[
                {
                    "expense_date": frappe.form_dict.expense_date,
                    "expense_type": frappe.form_dict.expense_type,
                    "description": frappe.form_dict.description,
                    "amount": frappe.form_dict.amount,
                }
            ],
            posting_date=today(),
            company=emp_data.get("company"),
            payable_account=payable_account,
        ).insert()

        if "file" in frappe.request.files:
            file = upload_file()
            file.attached_to_doctype = "Expense Claim"
            file.attached_to_name = expense_doc.name
            file.save(ignore_permissions=True)

        return gen_response(200, "Expense applied Successfully", expense_doc)
    except Exception as e:
        return exception_handler(e)

def send_notification_for_task_assign(doc, event):
    from frappe.utils.data import strip_html

    if doc.status == "Open" and doc.reference_type == "Task":
        filters = [["Task", "name", "=", f"{doc.reference_name}"]]
        task = frappe.db.get_value(
            "Task", filters, ["subject", "description"], as_dict=1
        )
        create_push_notification(
            title=f"New Task Assigned - {task.get('subject')}",
            message=(
                strip_html(str(task.get("description")))
                if task.get("description")
                else ""
            ),
            send_for="Single User",
            user=doc.allocated_to,
            notification_type="task_assignment",
        )

