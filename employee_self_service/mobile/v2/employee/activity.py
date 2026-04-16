import frappe
from frappe import _
from employee_self_service.mobile.v2.employee.utils import *


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
