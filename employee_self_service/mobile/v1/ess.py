import json
import os
import calendar
import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import (
    cstr,
    get_date_str,
    today,
    nowdate,
    getdate,
    now_datetime,
    get_first_day,
    get_last_day,
    date_diff,
    flt,
    pretty_date,
    fmt_money,
    add_days,
    format_time,
)
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    generate_key,
    ess_validate,
    get_employee_by_user,
    validate_employee_data,
    get_ess_settings,
    get_global_defaults,
    exception_handler,
)

from erpnext.accounts.utils import get_fiscal_year

from employee_self_service.employee_self_service.doctype.push_notification.push_notification import (
    create_push_notification,
)


@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(usr, pwd)
        validate_employee(login_manager.user)
        login_manager.post_login()
        if frappe.response["message"] == "Logged In":
            emp_data = get_employee_by_user(login_manager.user)
            frappe.response["user"] = login_manager.user
            frappe.response["key_details"] = generate_key(login_manager.user)
            frappe.response["employee_id"] = emp_data.get("name")
        gen_response(200, frappe.response["message"])
    except frappe.AuthenticationError:
        gen_response(500, frappe.response["message"])
    except Exception as e:
        return exception_handler(e)


def validate_employee(user):
    if not frappe.db.exists("Employee", dict(user_id=user)):
        frappe.response["message"] = "Please link Employee with this user"
        raise frappe.AuthenticationError(frappe.response["message"])


@frappe.whitelist()
@ess_validate(methods=["POST"])
def make_leave_application(*args, **kwargs):
    try:
        from erpnext.hr.doctype.leave_application.leave_application import (
            get_leave_approver,
        )

        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists!")
        validate_employee_data(emp_data)
        leave_application_doc = frappe.get_doc(
            dict(
                doctype="Leave Application",
                employee=emp_data.get("name"),
                company=emp_data.company,
                leave_approver=get_leave_approver(emp_data.name),
            )
        )
        leave_application_doc.update(kwargs)
        res = leave_application_doc.insert()
        gen_response(200, "Leave application successfully added!")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_leave_type(from_date=None, to_date=None):
    try:
        from erpnext.hr.doctype.leave_application.leave_application import (
            get_leave_balance_on,
        )

        if not from_date:
            from_date = today()
        emp_data = get_employee_by_user(frappe.session.user)
        leave_types = frappe.get_all(
            "Leave Type", filters={}, fields=["name", "'0' as balance"]
        )
        for leave_type in leave_types:
            leave_type["balance"] = get_leave_balance_on(
                emp_data.get("name"),
                leave_type.get("name"),
                from_date,
                consider_all_leaves_in_the_allocation_period=True,
            )
        return gen_response(200, "Leave type get successfully", leave_types)
    except Exception as e:
        return exception_handler(e)


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
        ]
        upcoming_leaves = frappe.get_all(
            "Leave Application",
            filters={"from_date": [">", today()], "employee": emp_data.get("name")},
            fields=leave_application_fields,
        )

        taken_leaves = frappe.get_all(
            "Leave Application",
            fields=leave_application_fields,
            filters={"from_date": ["<=", today()], "employee": emp_data.get("name")},
        )
        fiscal_year = get_fiscal_year(nowdate())[0]
        if not fiscal_year:
            return gen_response(500, "Fiscal year not set")
        res = get_leave_balance_report(
            emp_data.get("name"), emp_data.get("company"), fiscal_year
        )

        leave_applications = {
            "upcoming": upcoming_leaves,
            "taken": taken_leaves,
            "balance": res["result"],
        }
        return gen_response(200, "Leave data getting successfully", leave_applications)
    except Exception as e:
        return exception_handler(e)


def get_leave_balance_report(employee, company, fiscal_year):
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

    result = run("Employee Leave Balance", filters=filters_leave_balance)
    for row in result.get("result"):
        frappe.log_error(title="180", message=row)
        frappe.log_error(title="180", message=type(row.get("employee")))
        if isinstance(row.get("employee"), tuple):
            row["employee"] = employee
    return result


@frappe.whitelist()
def get_expense_type():
    try:
        expense_types = frappe.get_all(
            "Expense Claim Type", filters={}, fields=["name"]
        )
        return gen_response(200, "Expense type get successfully", expense_types)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def book_expense(*args, **kwargs):
    try:
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "company", "expense_approver"]
        )
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)
        data = kwargs
        payable_account = get_payable_account(emp_data.get("company"))
        expense_doc = frappe.get_doc(
            dict(
                doctype="Expense Claim",
                employee=emp_data.name,
                expense_approver=emp_data.expense_approver,
                expenses=[
                    {
                        "expense_date": data.get("expense_date"),
                        "expense_type": data.get("expense_type"),
                        "description": data.get("description"),
                        "amount": data.get("amount"),
                    }
                ],
                posting_date=today(),
                company=emp_data.get("company"),
                payable_account=payable_account,
            )
        ).insert()
        # expense_doc.submit()
        if not data.get("attachments") == None:
            for file in data.get("attachments"):
                frappe.db.set_value(
                    "File", file.get("name"), "attached_to_name", expense_doc.name
                )
        return gen_response(200, "Expense applied successfully", expense_doc)
    except Exception as e:
        return exception_handler(e)


def get_payable_account(company):
    ess_settings = get_ess_settings()
    default_payable_account = ess_settings.get("default_payable_account")
    if not default_payable_account:
        default_payable_account = frappe.db.get_value(
            "Company", company, "default_payable_account"
        )
        if not default_payable_account:
            return gen_response(
                500,
                "Set Default Payable Account Either In ESS Settings or Company Settings",
            )
        else:
            return default_payable_account
    return default_payable_account


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_expense_list():
    try:
        global_defaults = get_global_defaults()
        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)
        expense_list = frappe.get_all(
            "Expense Claim",
            filters={"employee": emp_data.get("name")},
            fields=["*"],
        )
        expense_data = {}
        for expense in expense_list:
            (
                expense["expense_type"],
                expense["expense_description"],
                expense["expense_date"],
            ) = frappe.get_value(
                "Expense Claim Detail",
                {"parent": expense.name},
                ["expense_type", "description", "expense_date"],
            )
            expense["expense_date"] = expense["expense_date"].strftime("%d-%m-%Y")
            expense["posting_date"] = expense["posting_date"].strftime("%d-%m-%Y")
            expense["total_claimed_amount"] = fmt_money(
                expense["total_claimed_amount"],
                currency=global_defaults.get("default_currency"),
            )
            expense["attachments"] = frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": "Expense Claim",
                    "attached_to_name": expense.name,
                    "is_folder": 0,
                },
                fields=["file_url"],
            )

            month_year = get_month_year_details(expense)
            if not month_year in list(expense_data.keys())[::-1]:
                expense_data[month_year] = [expense]
            else:
                expense_data[month_year].append(expense)
        return gen_response(200, "Expense date get successfully", expense_data)
    except Exception as e:
        return exception_handler(e)


def get_month_year_details(expense):
    date = getdate(expense.get("posting_date"))
    month = date.strftime("%B")
    year = date.year
    return f"{month} {year}"


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_salary_sllip():
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)
        salary_slip_list = frappe.get_all(
            "Salary Slip",
            filters={"employee": emp_data.get("name")},
            fields=["posting_date", "name"],
        )
        ss_data = []
        for ss in salary_slip_list:
            ss_details = {}
            month_year = get_month_year_details(ss)
            ss_details["month_year"] = month_year
            ss_details["salary_slip_id"] = ss.name
            ss_details["details"] = get_salary_slip_details(ss.name)
            ss_data.append(ss_details)
        return gen_response(200, "Salary slip details get successfully", ss_data)
    except Exception as e:
        return exception_handler(e)


def get_salary_slip_details(ss_id):
    return frappe.get_doc("Salary Slip", ss_id)


@frappe.whitelist()
@ess_validate(methods=["GET", "POST"])
def download_salary_slip(ss_id):
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        res = frappe.get_doc("Salary Slip", ss_id)
        if not emp_data.get("name") == res.get("employee"):
            return gen_response(
                500, "Does not have persmission to read this salary slip"
            )
        default_print_format = frappe.db.get_value(
            "Employee Self Service Settings",
            "Employee Self Service Settings",
            "default_print_format",
        )
        if not default_print_format:
            default_print_format = (
                frappe.db.get_value(
                    "Property Setter",
                    dict(property="default_print_format", doc_type=res.doctype),
                    "value",
                )
                or "Standard"
            )
        language = frappe.get_system_settings("language")
        # return  frappe.utils.get_url()
        # url = f"{ frappe.utils.get_url() }/{ res.doctype }/{ res.name }?format={ default_print_format or 'Standard' }&_lang={ language }&key={ res.get_signature() }"
        # return url
        download_pdf(res.doctype, res.name, default_print_format, res)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def download_pdf(doctype, name, format=None, doc=None, no_letterhead=0):
    from frappe.utils.pdf import get_pdf, cleanup

    html = frappe.get_print(doctype, name, format, doc=doc, no_letterhead=no_letterhead)
    frappe.local.response.filename = "{name}.pdf".format(
        name=name.replace(" ", "-").replace("/", "-")
    )
    frappe.local.response.filecontent = get_pdf(html)
    frappe.local.response.type = "download"


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard():
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["name", "company"])
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
            "last_log_time": log_details.get("time").strftime("%I:%M%p")
            if log_details.get("time")
            else "",
            "check_in_with_image": settings.get("check_in_with_image"),
            "check_in_with_location": settings.get("check_in_with_location"),
            "quick_task": settings.get("quick_task"),
            "allow_odometer_reading_input": settings.get(
                "allow_odometer_reading_input"
            ),
        }
        dashboard_data["employee_image"] = frappe.get_cached_value(
            "Employee", emp_data.get("name"), "image"
        )
        get_latest_expense(dashboard_data, emp_data.get("name"))
        get_latest_ss(dashboard_data, emp_data.get("name"))
        get_last_log_type(dashboard_data, emp_data.get("name"))
        return gen_response(200, "Dashboard data get successfully", dashboard_data)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_leave_balance_dashboard():
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["name", "company"])
        fiscal_year = get_fiscal_year(nowdate())[0]
        dashboard_data = {"leave_balance": []}
        if fiscal_year:
            res = get_leave_balance_report(
                emp_data.get("name"), emp_data.get("company"), fiscal_year
            )
            dashboard_data["leave_balance"] = res["result"]
        return gen_response(200, "Leave balance data get successfully", dashboard_data)
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


def get_attendance_details(emp_data):
    last_date = get_last_day(today())
    first_date = get_first_day(today())
    total_days = date_diff(last_date, first_date)
    till_date_days = date_diff(today(), first_date)
    days_off = 0
    absent = 0
    total_present = 0
    attendance_report = run_attendance_report(
        emp_data.get("name"), emp_data.get("company")
    )
    if attendance_report:
        days_off = flt(attendance_report.get("total_leaves")) + flt(
            attendance_report.get("total_holidays")
        )
        absent = till_date_days - (
            flt(days_off) + flt(attendance_report.get("total_present"))
        )
        total_present = attendance_report.get("total_present")
    attendance_details = {
        "month_title": f"{frappe.utils.getdate().strftime('%B')} Details",
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
def run_attendance_report(employee, company):
    filters = {
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


def get_latest_expense(dashboard_data, employee):
    global_defaults = get_global_defaults()
    expense_list = frappe.get_all(
        "Expense Claim",
        filters={"employee": employee},
        fields=["name"],
        order_by="modified desc",
    )
    if len(expense_list) >= 1:
        expense_doc = frappe.get_doc("Expense Claim", expense_list[0].name)
        dashboard_data["latest_expense"] = dict(
            status=expense_doc.approval_status,
            date=expense_doc.expenses[0].expense_date.strftime("%d-%m-%Y"),
            expense_type=expense_doc.expenses[0].expense_type,
            # amount=expense_doc.expenses[0].amount,
            amount=fmt_money(
                expense_doc.expenses[0].amount,
                currency=global_defaults.get("default_currency"),
            ),
            name=expense_doc.name,
        )


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


@frappe.whitelist()
def create_employee_log(
    log_type, location=None, odometer_reading=None, attendance_image=None
):
    try:
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "default_shift"]
        )
        log_doc = frappe.get_doc(
            dict(
                doctype="Employee Checkin",
                employee=emp_data.get("name"),
                log_type=log_type,
                time=now_datetime().__str__()[:-7],
                location=location,
                odometer_reading=odometer_reading,
                attendance_image=attendance_image,
            )
        ).insert(ignore_permissions=True)
        # update_shift_last_sync(emp_data)
        return gen_response(200, "Employee log added")
    except Exception as e:
        return exception_handler(e)


def update_shift_last_sync(emp_data):
    if emp_data.get("default_shift"):
        frappe.db.set_value(
            "Shift Type",
            emp_data.get("default_shift"),
            "last_sync_of_checkin",
            now_datetime(),
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
            doc = frappe.get_doc(
                dict(
                    doctype="Notice Board",
                    notice_title=title,
                    message=message,
                    from_date=today(),
                    to_date=today(),
                    apply_for="Specific Employees",
                    employees=[dict(employee=emp.get("emp_id"))],
                )
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


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_list():
    try:
        tasks = frappe.get_all(
            "Task",
            fields=[
                "name",
                "subject",
                "project",
                "priority",
                "status",
                "description",
                "exp_end_date",
                "_assign as assigned_to",
                "owner as assigned_by",
            ],
            filters={"_assign": ["like", f"%{frappe.session.user}%"]},
        )
        completed_task = []
        incomplete_task = []

        for task in tasks:
            if task["exp_end_date"]:
                task["exp_end_date"] = task["exp_end_date"].strftime("%d-%m-%Y")
            comments = frappe.get_all(
                "Comment",
                filters={
                    "reference_name": ["like", "%{0}%".format(task.get("name"))],
                    "comment_type": "Comment",
                },
                fields=[
                    "content as comment",
                    "comment_by",
                    "reference_name",
                    "creation",
                    "comment_email",
                ],
            )
            task["project_name"] = frappe.db.get_value(
                "Project", {"name": task.get("project")}, ["project_name"]
            )

            task["assigned_by"] = frappe.db.get_value(
                "User",
                {"name": task.get("assigned_by")},
                ["full_name as user", "user_image"],
                as_dict=1,
            )

            task["assigned_to"] = frappe.get_all(
                "User",
                filters=[["User", "email", "in", json.loads(task.get("assigned_to"))]],
                fields=["full_name as user", "user_image"],
                order_by="creation asc",
            )

            for comment in comments:
                comment["commented"] = pretty_date(comment["creation"])
                comment["creation"] = comment["creation"].strftime("%I:%M %p")
                user_image = frappe.get_value(
                    "User", comment.comment_email, "user_image", cache=True
                )
                comment["user_image"] = user_image

            task["comments"] = comments
            task["num_comments"] = len(comments)

            if task.status == "Completed":
                completed_task.append(task)
            else:
                incomplete_task.append(task)

        response_data = {"tasks": incomplete_task, "completed_tasks": completed_task}

        return gen_response(200, "Task list getting Successfully", response_data)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_task_status():
    try:
        if not frappe.request.json.get("task_id") or not frappe.request.json.get(
            "new_status"
        ):
            return gen_response(500, "task id and new status is required")
        assigned_to = frappe.get_value(
            "Task",
            {"name": frappe.request.json.get("task_id")},
            ["_assign", "status"],
            cache=True,
            as_dict=True,
        )

        if assigned_to.get("_assign") == None:
            return gen_response(500, "Task Not assigned for any user")

        elif frappe.session.user not in assigned_to.get("_assign"):
            return gen_response(500, "You are not authorized to update this task")

        elif frappe.request.json.get("new_status") not in frappe.get_meta(
            "Task"
        ).get_field("status").options.split("\n"):
            return gen_response(500, "Task status invalid")

        elif assigned_to.get("status") == frappe.request.json.get("new_status"):
            return gen_response(500, "status already up-to-date")

        task_doc = frappe.get_doc("Task", frappe.request.json.get("task_id"))
        task_doc.status = frappe.request.json.get("new_status")
        if task_doc.status == "Completed":
            task_doc.completed_by = frappe.session.user
            task_doc.completed_on = today()
        task_doc.save()
        return gen_response(200, "Task status updated successfully")

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_holiday_list(year=None):
    try:
        if not year:
            return gen_response(500, "year is required")
        emp_data = get_employee_by_user(frappe.session.user)

        from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee

        holiday_list = get_holiday_list_for_employee(
            emp_data.name, raise_exception=False
        )

        if not holiday_list:
            return gen_response(200, "Holiday list get successfully", [])

        holidays = frappe.get_all(
            "Holiday",
            filters={
                "parent": holiday_list,
                "holiday_date": ("between", [f"{year}-01-01", f"{year}-12-31"]),
            },
            fields=["description", "holiday_date"],
            order_by="holiday_date asc",
        )

        if len(holidays) == 0:
            return gen_response(500, f"no holidays found for year {year}")

        holiday_list = []

        for holiday in holidays:
            holiday_date = frappe.utils.data.getdate(holiday.holiday_date)
            holiday_list.append(
                {
                    "year": holiday_date.strftime("%Y"),
                    "date": holiday_date.strftime("%d %b"),
                    "day": holiday_date.strftime("%A"),
                    "description": holiday.description,
                }
            )
        return gen_response(200, "Holiday list get successfully", holiday_list)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_list_dashboard():
    try:
        filters = [
            ["_assign", "like", f"%{frappe.session.user}%"],
            ["status", "!=", "Completed"],
        ]
        tasks = frappe.get_all(
            "Task",
            fields=[
                "name",
                "subject",
                "project",
                "priority",
                "status",
                "description",
                "exp_end_date",
                "_assign as assigned_to",
                "owner as assigned_by",
            ],
            filters=filters,
            limit=4,
        )
        for task in tasks:
            if task["exp_end_date"]:
                task["exp_end_date"] = task["exp_end_date"].strftime("%d-%m-%Y")
            comments = frappe.get_all(
                "Comment",
                filters={
                    "reference_name": ["like", "%{0}%".format(task.get("name"))],
                    "comment_type": "Comment",
                },
                fields=[
                    "content as comment",
                    "comment_by",
                    "reference_name",
                    "creation",
                    "comment_email",
                ],
            )

            project_name = frappe.db.get_value(
                "Project", {"name": task.get("project")}, ["project_name"]
            )
            task["project_name"] = project_name

            assigned_by = frappe.db.get_value(
                "User",
                {"name": task.get("assigned_by")},
                ["full_name as user", "user_image"],
                as_dict=1,
            )
            task["assigned_by"] = assigned_by

            for comment in comments:
                comment["commented"] = pretty_date(comment["creation"])
                comment["creation"] = comment["creation"].strftime("%I:%M %p")
                user_image = frappe.get_value(
                    "User", comment.comment_email, "user_image", cache=True
                )
                comment["user_image"] = user_image

            assigned_to = frappe.get_all(
                "User",
                filters=[["User", "email", "in", json.loads(task.get("assigned_to"))]],
                fields=["full_name as user", "user_image"],
                order_by="creation asc",
            )

            task["assigned_to"] = assigned_to

            task["comments"] = comments
            task["num_comments"] = len(comments)

        return gen_response(200, "Task list get successfully", tasks)
    except Exception as e:
        return exception_handler(e)


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

        for attendance in employee_attendance_list:
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
@ess_validate(methods=["POST"])
def add_comment(reference_doctype=None, reference_name=None, content=None):
    try:
        from frappe.desk.form.utils import add_comment

        comment_by = frappe.db.get_value(
            "User", frappe.session.user, "full_name", as_dict=1
        )

        add_comment(
            reference_doctype=reference_doctype,
            reference_name=reference_name,
            content=content,
            comment_email=frappe.session.user,
            comment_by=comment_by.get("full_name"),
        )
        return gen_response(200, "Comment added successfully")

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_comments(reference_doctype=None, reference_name=None):
    """
    reference_doctype: doctype
    reference_name: docname
    """
    try:
        filters = [
            ["Comment", "reference_doctype", "=", f"{reference_doctype}"],
            ["Comment", "reference_name", "=", f"{reference_name}"],
            ["Comment", "comment_type", "=", "Comment"],
        ]
        comments = frappe.get_all(
            "Comment",
            filters=filters,
            fields=[
                "content as comment",
                "comment_by",
                "creation",
                "comment_email",
            ],
        )

        for comment in comments:
            user_image = frappe.get_value(
                "User", comment.comment_email, "user_image", cache=True
            )
            comment["user_image"] = user_image
            comment["commented"] = pretty_date(comment["creation"])
            comment["creation"] = comment["creation"].strftime("%I:%M %p")

        return gen_response(200, "Comments get successfully", comments)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_profile():
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        employee_details = frappe.get_cached_value(
            "Employee",
            emp_data.get("name"),
            [
                "employee_name",
                "designation",
                "name",
                "date_of_joining",
                "date_of_birth",
                "gender",
                "company_email",
                "personal_email",
                "cell_number",
                "emergency_phone_number",
            ],
            as_dict=True,
        )
        employee_details["date_of_joining"] = employee_details[
            "date_of_joining"
        ].strftime("%d-%m-%Y")
        employee_details["date_of_birth"] = employee_details["date_of_birth"].strftime(
            "%d-%m-%Y"
        )

        employee_details["employee_image"] = frappe.get_cached_value(
            "Employee", emp_data.get("name"), "image"
        )

        return gen_response(200, "Profile get successfully", employee_details)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def upload_documents():
    try:
        emp_data = get_employee_by_user(frappe.session.user)

        from frappe.handler import upload_file

        file_doc = upload_file()

        ess_document = frappe.get_doc(
            {
                "doctype": "ESS Documents",
                "employee_no": emp_data.get("name"),
                "title": frappe.form_dict.title,
            }
        ).insert()

        file_doc.attached_to_doctype = "ESS Documents"
        file_doc.attached_to_name = str(ess_document.name)
        file_doc.attached_to_field = "attachement"
        file_doc.save()

        ess_document.attachement = file_doc.file_url
        ess_document.save()

        return gen_response(200, "Document added successfully")
    except Exception as e:
        return exception_handler(e)


def get_file_size(file_path, unit="auto"):
    file_size = os.path.getsize(file_path)

    units = ["B", "Kb", "Mb", "Gb", "Tb"]
    if unit == "auto":
        unit_index = 0
        while file_size > 1000:
            file_size /= 1000
            unit_index += 1
            if unit_index == len(units) - 1:
                break
        unit = units[unit_index]
    else:
        unit_index = units.index(unit)

    return f"{file_size:.2f}{unit}"


@frappe.whitelist()
@ess_validate(methods=["GET"])
def document_list():
    try:
        from frappe.utils.file_manager import get_file_path

        emp_data = get_employee_by_user(frappe.session.user)
        documents = frappe.get_all(
            "ESS Documents",
            filters={
                "employee_no": emp_data.get("name"),
            },
            fields=["name", "attachement"],
        )

        if documents:
            for doc in documents:
                file = frappe.get_value(
                    "File",
                    {
                        "file_url": doc.get("attachement"),
                        "attached_to_doctype": "ESS Documents",
                        "attached_to_name": doc.get("name"),
                    },
                    ["name", "file_name", "file_size"],
                    as_dict=1,
                )
                if file:
                    doc["file_name"] = file.get("file_name")
                    doc["file_size"] = get_file_size(
                        (get_file_path(file.get("file_name"))), unit="auto"
                    )
                    doc["file_id"] = file.get("name")

            return gen_response(200, "Documents get successfully", documents)
        else:
            return gen_response(500, "No documents found for employee", [])
    except Exception as e:
        return exception_handler(e)


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
    from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee

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


@frappe.whitelist()
@ess_validate(methods=["POST"])
def employee_device_info(**kwargs):
    try:
        data = kwargs
        existing_token = frappe.db.get_value(
            "Employee Device Info",
            filters={"user": frappe.session.user},
            fieldname="name",
        )
        if frappe.db.exists("Employee Device Info", existing_token):
            token = frappe.get_doc("Employee Device Info", existing_token)
            token.platform = data.get("platform")
            token.os_version = data.get("os_version")
            token.device_name = data.get("device_name")
            token.app_version = data.get("app_version")
            token.token = data.get("token")
            token.save(ignore_permissions=True)
        else:
            token = frappe.get_doc(
                dict(
                    doctype="Employee Device Info",
                    platform=data.get("platform"),
                    os_version=data.get("os_version"),
                    device_name=data.get("device_name"),
                    app_version=data.get("app_version"),
                    token=data.get("token"),
                    user=frappe.session.user,
                )
            ).insert(ignore_permissions=True)

        return gen_response(200, "Device information saved successfully!")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def notification_list():
    try:
        single_filters = [
            ["Push Notification", "user", "=", frappe.session.user],
            ["Push Notification", "send_for", "=", "Single User"],
        ]
        notification = frappe.get_all(
            "Push Notification",
            filters=single_filters,
            fields=["title", "message", "creation"],
        )
        multiple_filters = [
            ["Notification User", "user", "=", frappe.session.user],
            ["Push Notification", "send_for", "=", "Multiple User"],
        ]
        multiple_notification = frappe.get_all(
            "Push Notification",
            filters=multiple_filters,
            fields=["title", "message"],
        )
        notification.extend(multiple_notification)
        all_filters = [["Push Notification", "send_for", "=", "All User"]]

        all_notification = frappe.get_all(
            "Push Notification",
            filters=all_filters,
            fields=["title", "message"],
        )

        notification.extend(all_notification)

        for notified in notification:
            notified["creation"] = pretty_date(notified.get("creation"))
            notified["user_image"] = frappe.get_value(
                "User", frappe.session.user, "user_image"
            )
        return gen_response(200, "Notification list get successfully", notification)
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


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_branch():
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["branch"])
        branch = frappe.db.get_value(
            "Branch",
            {"branch": emp_data.get("branch")},
            ["branch", "latitude", "longitude", "radius"],
            as_dict=1,
        )

        return gen_response(200, "Branch", branch)
    except Exception as e:
        return exception_handler(e)


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


@frappe.whitelist()
def change_password(data):
    try:
        from frappe.utils.password import check_password, update_password

        user = frappe.session.user
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        check_password(user, current_password)
        update_password(user, new_password)
        return gen_response(200, "Password updated")
    except frappe.AuthenticationError:
        return gen_response(500, "Incorrect current password")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_by_id(task_id=None):
    try:
        if not task_id:
            return gen_response(500, "task_id is required", [])
        # filters = [
        #     ["Task", "name", "=", task_id],
        #     ["Task", "_assign", "like", f"%{frappe.session.user}%"],
        # ]
        tasks = frappe.db.get_value(
            "Task",
            {"name": task_id},
            [
                "name",
                "subject",
                "project",
                "priority",
                "status",
                "description",
                "exp_end_date",
                "_assign as assigned_to",
                "owner as assigned_by",
            ],
            as_dict=1,
        )
        if not tasks:
            return gen_response(500, "you have not task with this task id", [])

        assigned_by = frappe.db.get_value(
            "User",
            {"name": tasks.get("assigned_by")},
            ["full_name as user", "user_image"],
            as_dict=1,
        )
        tasks["assigned_by"] = assigned_by

        project_name = frappe.db.get_value(
            "Project", {"name": tasks.get("project")}, ["project_name"]
        )
        tasks["project_name"] = project_name

        assigned_to = frappe.get_all(
            "User",
            filters=[["User", "email", "in", json.loads(tasks.get("assigned_to"))]],
            fields=["full_name as user", "user_image"],
            order_by="creation asc",
        )

        tasks["assigned_to"] = assigned_to

        comments = frappe.get_all(
            "Comment",
            filters={
                "reference_name": ["like", "%{0}%".format(tasks.get("name"))],
                "comment_type": "Comment",
            },
            fields=[
                "content as comment",
                "comment_by",
                "reference_name",
                "creation",
                "comment_email",
            ],
        )

        for comment in comments:
            comment["commented"] = pretty_date(comment["creation"])
            comment["creation"] = comment["creation"].strftime("%I:%M %p")
            user_image = frappe.get_value(
                "User", comment.comment_email, "user_image", cache=True
            )
            comment["user_image"] = user_image

        tasks["comments"] = comments
        tasks["num_comments"] = len(comments)

        return gen_response(200, "Task", tasks)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read task")
    except Exception as e:
        return exception_handler(e)


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
            dict(
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
            )
        ).insert()

        from frappe.handler import upload_file

        if "file" in frappe.request.files:
            file = upload_file()
            file.attached_to_doctype = "Expense Claim"
            file.attached_to_name = expense_doc.name
            file.save(ignore_permissions=True)

        return gen_response(200, "Expense applied Successfully", expense_doc)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_profile_picture():
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        from frappe.handler import upload_file

        employee_profile_picture = upload_file()
        employee_profile_picture.attached_to_doctype = "Employee"
        employee_profile_picture.attached_to_name = emp_data.get("name")
        employee_profile_picture.attached_to_field = "image"
        employee_profile_picture.save(ignore_permissions=True)

        frappe.db.set_value(
            "Employee", emp_data.get("name"), "image", employee_profile_picture.file_url
        )
        if employee_profile_picture:
            frappe.db.set_value(
                "User",
                frappe.session.user,
                "user_image",
                employee_profile_picture.file_url,
            )
        return gen_response(200, "Employee profile picture updated successfully")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_transactions(
    from_date=None, to_date=None, party_type=None, party=None, download="false"
):
    try:
        from_date = getdate(from_date)
        to_date = getdate(to_date)
        if not from_date or not to_date:
            frappe.throw(_("Select First from date and to date"))
        global_defaults = get_global_defaults()
        if not party_type:
            party_type = "Employee"
        if not party:
            emp_data = get_employee_by_user(frappe.session.user)
            party = [emp_data.get("name")]
        allowed_party_types = ["Employee", "Customer"]

        if party_type not in allowed_party_types:
            frappe.throw(
                _("Invalid party type. Allowed party types are {0}").format(
                    ", ".join(allowed_party_types)
                )
            )
        filters_report = {
            "company": global_defaults.get("default_company"),
            "from_date": from_date,
            "to_date": to_date,
            "account": [],
            "party_type": party_type,
            "party": party,
            "group_by": "Group by Party",
            "cost_center": [],
            "project": [],
            "include_dimensions": 1,
        }
        if party_type == "Employee" and isinstance(party, list) and len(party) == 1:
            filters_report["party_name"] = frappe.db.get_value(
                party_type, party[0], "employee_name"
            )
        else:
            filters_report["party_name"] = (
                ", ".join(party) if party and len(party) > 0 else ""
            )

        from frappe.desk.query_report import run

        res = run("General Ledger", filters=filters_report, ignore_prepared_report=True)
        data = []
        total = {}
        opening_balance = {}
        if res.get("result"):
            for row in res.get("result"):
                if "gl_entry" in row.keys():
                    data.append(
                        {
                            "posting_date": row.get("posting_date").strftime(
                                "%d-%m-%Y"
                            ),
                            "voucher_type": row.get("voucher_type"),
                            "voucher_no": row.get("voucher_no"),
                            "debit": fmt_money(
                                row.get("debit"),
                                currency=global_defaults.get("default_currency"),
                            ),
                            "credit": fmt_money(
                                row.get("credit"),
                                currency=global_defaults.get("default_currency"),
                            ),
                            "balance": fmt_money(
                                row.get("balance"),
                                currency=global_defaults.get("default_currency"),
                            ),
                            "party_type": row.get("party_type"),
                            "party": row.get("party"),
                        }
                    )

                    if flt(row.get("balance")) >= 0:
                        row["color"] = "red"
                    else:
                        row["color"] = "green"
                if "'Opening'" in row.values():
                    opening_balance = {
                        "account": "Opening",
                        "posting_date": from_date.strftime("%d-%m-%Y"),
                        "credit": fmt_money(
                            row.get("credit"),
                            currency=global_defaults.get("default_currency"),
                        ),
                        "debit": fmt_money(
                            row.get("debit"),
                            currency=global_defaults.get("default_currency"),
                        ),
                        "balance": fmt_money(
                            row.get("balance"),
                            currency=global_defaults.get("default_currency"),
                        ),
                    }
                if "'Total'" in row.values():
                    total = {
                        "account": "Total",
                        "posting_date": to_date.strftime("%d-%m-%Y"),
                        "credit": fmt_money(
                            row.get("credit"),
                            currency=global_defaults.get("default_currency"),
                        ),
                        "debit": fmt_money(
                            row.get("debit"),
                            currency=global_defaults.get("default_currency"),
                        ),
                        "balance": fmt_money(
                            row.get("balance"),
                            currency=global_defaults.get("default_currency"),
                        ),
                    }
            data.insert(0, opening_balance)
            data.append(total)

            from frappe.utils.print_format import report_to_pdf

            if download == "true":
                html = frappe.render_template(
                    "employee_self_service/templates/employee_statement.html",
                    {
                        "data": data,
                        "filters": filters_report,
                        "user": frappe.db.get_value(
                            "User", frappe.session.user, "full_name"
                        ),
                    },
                    is_path=True,
                )
                return report_to_pdf(html)
        return gen_response(200, "Ledger Get Successfully", data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted general ledger report")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_customer_list():
    try:
        customer = frappe.get_list("Customer", ["name", "customer_name"])
        return gen_response(200, "Customr list Getting Successfully", customer)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read customer")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_list():
    try:
        employee = frappe.get_list("Employee", ["name", "employee_name"])
        return gen_response(200, "Employee list Getting Successfully", employee)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read employee")
    except Exception as e:
        return exception_handler(e)


def send_notification_for_task_assign(doc, event):
    from frappe.utils.data import strip_html

    if doc.status == "Open" and doc.reference_type == "Task":
        task_doc = frappe.get_doc(doc.reference_type, doc.reference_name)
        # filters = [["Task", "name", "=", f"{doc.reference_name}"]]
        # task = frappe.db.get_value(
        #     "Task", filters, ["subject", "description"], as_dict=1
        # )
        create_push_notification(
            title=f"New Task Assigned - {task_doc.get('subject')}",
            message=strip_html(str(task_doc.get("description")))
            if task_doc.get("description")
            else "",
            send_for="Single User",
            user=doc.owner,
            notification_type="task_assignment",
        )


@frappe.whitelist()
@ess_validate(methods=["DELETE"])
def delete_documents(file_id=None, attached_to_name=None):
    try:
        from frappe.utils.file_manager import remove_file

        attached_to_doctype = "ESS Documents"
        remove_file(
            fid=file_id,
            attached_to_doctype=attached_to_doctype,
            attached_to_name=attached_to_name,
        )
        frappe.delete_doc(attached_to_doctype, attached_to_name, force=1)
        return gen_response(200, "you have successfully deleted ESS Document")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted delete file")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_task(**kwargs):
    try:
        from frappe.desk.form import assign_to

        data = json.loads(frappe.request.get_data())
        task_assign_to = data.get("assign_to")
        del data["assign_to"]
        frappe.log_error(title="data", message=data)
        task_doc = frappe.new_doc("Task")
        task_doc.update(data)
        task_doc = task_doc.insert()
        frappe.log_error(title="assign", message=assign_to)
        if task_assign_to:
            assign_to.add(
                {
                    "assign_to": task_assign_to,
                    "doctype": task_doc.doctype,
                    "name": task_doc.name,
                }
            )
        return gen_response(200, "Task has been created successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for create task")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_quick_task(**kwargs):
    try:
        from frappe.desk.form import assign_to

        data = kwargs
        task_doc = frappe.get_doc(dict(doctype="Task"))
        task_doc.update(data)
        task_doc.exp_end_date = today()
        task_doc.insert()
        assign_to.add(
            {
                "assign_to": [frappe.session.user],
                "doctype": task_doc.doctype,
                "name": task_doc.name,
            }
        )
        return gen_response(200, "Task has been created successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for create task")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_task(**kwargs):
    try:
        from frappe.desk.form import assign_to

        data = kwargs
        task_doc = frappe.get_doc("Task", data.get("name"))
        task_doc.update(data)
        task_doc.save()
        if data.get("assign_to"):
            assign_to.add(
                {
                    "assign_to": data.get("assign_to"),
                    "doctype": task_doc.doctype,
                    "name": task_doc.name,
                }
            )
        return gen_response(200, "Task has been updated successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for update task")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_quick_task_list():
    try:
        tasks = frappe.get_all(
            "Task",
            fields=["name", "subject", "exp_end_date", "status"],
            filters={
                "_assign": ["like", f"%{frappe.session.user}%"],
                "exp_end_date": ["=", today()],
            },
        )
        return gen_response(200, "Task list getting Successfully", tasks)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_project_list():
    try:
        project_list = frappe.get_list("Project", ["name", "project_name"])
        return gen_response(200, "Project List getting Successfully", project_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read project")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_user_list():
    try:
        user_list = frappe.get_list("User", ["name", "full_name", "user_image"])
        return gen_response(200, "User List getting Successfully", user_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read user")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_status_list():
    try:
        task_status = frappe.get_meta("Task").get_field("status").options or ""
        if task_status:
            task_status = task_status.split("\n")
        return gen_response(200, "Status get successfully", task_status)
    except Exception as e:
        return exception_handler(e)
