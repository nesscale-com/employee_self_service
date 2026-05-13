import frappe
from frappe import _
from employee_self_service.mobile.v2.module.expense.utils import *

@frappe.whitelist()
def get_expense_type():
    try:
        expense_types = frappe.get_all(
            "Expense Claim Type", filters={}, fields=["name"]
        )
        return gen_response(200, "Expense type get successfully", expense_types)
    except Exception as e:
        return exception_handler(e)