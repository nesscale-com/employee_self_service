from employee_self_service.mobile.v2.utils import *
import frappe
from frappe.utils import getdate

def get_month_year_details(expense):
    date = getdate(expense.get("posting_date"))
    month = date.strftime("%B")
    year = date.year
    return f"{month} {year}"

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

def get_attachments(id):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Expense Claim", "attached_to_name": id},
        fields=["file_url", "file_name"],
    )