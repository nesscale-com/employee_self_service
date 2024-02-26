import frappe
import json
from frappe import _
from frappe.utils import pretty_date, getdate, fmt_money
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    remove_default_fields,
    get_global_defaults,
)
from employee_self_service.mobile.v1.manager.manager_utils import get_action


@frappe.whitelist()
@ess_validate(methods=["GET"])
def my_team_expense_claim():
    try:
        global_defaults = get_global_defaults()
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "image", "department"]
        )
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        filters = [["employee", "!=", emp_data.get("name")]]
        expense_list = frappe.get_list("Expense Claim", filters=filters, fields=["*"])
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
            expense["department"] = emp_data.get("department")
            expense["user_image"] = emp_data.get("image")
            expense["workflow"] = False
            expense["action"] = get_action(
                "Expense Claim", expense.get("name"), expense.get("status"), expense
            )
        return gen_response(200, "Team expense claim get successfully", expense_list)
    except Exception as e:
        return exception_handler(e)
