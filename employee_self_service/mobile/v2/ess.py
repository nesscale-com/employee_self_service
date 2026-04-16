import calendar
import os
import frappe
from frappe import _
from frappe.handler import upload_file
from frappe.utils import *
from employee_self_service.employee_self_service.doctype.push_notification.push_notification import (
    create_push_notification,
)
from employee_self_service.mobile.v2.api_utils import *
from employee_self_service.mobile.v2.task import *
from employee_self_service.mobile.v2.transactions import *

# import apis from other modules due to mobile api versioning
from employee_self_service.mobile.v2.auth import *
from employee_self_service.mobile.v2.leave import *
from employee_self_service.mobile.v2.expense import get_expense_type,get_payable_account,book_expense
from employee_self_service.mobile.v2.attendance import (
    get_attendance_details_dashboard,
    run_attendance_report,
    get_attendance_details,
    get_attendance_list,
    get_attendance_list_by_date,
    get_attendance_details_by_month
)
from employee_self_service.mobile.v2.employee import *
from employee_self_service.mobile.v2.payment import get_transactions_old
from employee_self_service.mobile.v2.commen import *
from employee_self_service.mobile.v2.task import create_quick_task, get_quick_task_list
from employee_self_service.mobile.v2.notification import *
from employee_self_service.mobile.v2.dashboard import *

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


# # moved to expense.py
# @frappe.whitelist()
# @ess_validate(methods=["POST"])
# def apply_expense():
#     try:
#         emp_data = get_employee_by_user(
#             frappe.session.user, fields=["name", "company", "expense_approver"]
#         )

#         if not len(emp_data) >= 1:
#             return gen_response(500, "Employee does not exists")
#         validate_employee_data(emp_data)

#         payable_account = get_payable_account(emp_data.get("company"))
#         expense_doc = frappe.get_doc(
#             doctype="Expense Claim",
#             employee=emp_data.name,
#             expense_approver=emp_data.expense_approver,
#             expenses=[
#                 {
#                     "expense_date": frappe.form_dict.expense_date,
#                     "expense_type": frappe.form_dict.expense_type,
#                     "description": frappe.form_dict.description,
#                     "amount": frappe.form_dict.amount,
#                 }
#             ],
#             posting_date=today(),
#             company=emp_data.get("company"),
#             payable_account=payable_account,
#         ).insert()

#         if "file" in frappe.request.files:
#             file = upload_file()
#             file.attached_to_doctype = "Expense Claim"
#             file.attached_to_name = expense_doc.name
#             file.save(ignore_permissions=True)

#         return gen_response(200, "Expense applied Successfully", expense_doc)
#     except Exception as e:
#         return exception_handler(e)

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

