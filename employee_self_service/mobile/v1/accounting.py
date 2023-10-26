import frappe
import erpnext
from frappe import _
from frappe.utils import today, flt
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
)
from employee_self_service.mobile.v1.file import get_attchment


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_petty_expense_data():
    try:
        meta_data = {}
        meta_data["mode_of_payment"] = frappe.get_list("Mode of Payment", pluck="name")
        meta_data["company"] = frappe.get_list("Company", pluck="name")
        gen_response(200, "Petty Expense meta data get successfully", meta_data)
    except frappe.PermissionError as e:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_expense_account(company):
    try:
        accounts = frappe.get_list(
            "Account",
            filters={"company": company, "root_type": "Expense", "is_group": 0},
            fields=["name"],
        )
        return gen_response(200, "Account list get successfully", accounts)
    except frappe.PermissionError as e:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_cost_center(company):
    try:
        cost_centers = frappe.get_list(
            "Cost Center", filters={"company": company, "is_group": 0}, fields=["name"]
        )
        return gen_response(200, "Cost Center list get successfully", cost_centers)
    except frappe.PermissionError as e:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_default_company_cost_center(company):
    try:
        return gen_response(
            200,
            "default cost center get successfully",
            erpnext.get_default_cost_center(company),
        )
    except frappe.PermissionError as e:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def make_petty_expense_entry(*args, **data):
    try:
        if data.get("name"):
            petty_expense_entry_doc = frappe.get_doc("Petty Expense", data.get("name"))
        else:
            petty_expense_entry_doc = frappe.new_doc("Petty Expense")
        is_submit = data.get("submit")
        del data["submit"]
        petty_expense_entry_doc.update(data)
        if is_submit == True:
            petty_expense_entry_doc.submit()
        else:
            petty_expense_entry_doc.save()
        if data.get("attachments") is not None:
            for file in data.get("attachments"):
                frappe.get_doc(
                    dict(
                        doctype="File",
                        file_url=file.get("file_url"),
                        attached_to_doctype="Petty Expense",
                        attached_to_name=petty_expense_entry_doc.name,
                    )
                ).insert(ignore_permissions=True)
        return gen_response(200, "Petty expense entry saved")
    except frappe.PermissionError as e:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_petty_expense_list(start=0, page_length=10, filters=None):
    try:
        petty_expense_entry_list = frappe.get_list(
            "Petty Expense",
            fields=[
                "*",
            ],
            start=start,
            page_length=page_length,
            order_by="modified desc",
            filters=filters,
        )
        return gen_response(
            200,
            "petty expense entry details get successfully",
            petty_expense_entry_list,
        )
    except frappe.PermissionError as e:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_petty_expense_entry(id):
    try:
        if not id:
            return gen_response(500, "Petty Expense Entry id is required")
        if not frappe.db.exists("Petty Expense", id):
            return gen_response(500, "Petty Expense entry does not exists")
        petty_expense_entry = frappe.get_doc("Petty Expense", id).as_dict()

        petty_expense_entry["attachments"] = get_attchment("Petty Expense", id)
        return gen_response(
            200, "Petty Expense Entry get successfully", petty_expense_entry
        )
    except frappe.PermissionError as e:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)


"""get party by party type"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_party(party_type):
    try:
        if party_type == "Customer":
            meta_data = frappe.get_list(
                party_type, fields=["name", "customer_name as party_name"]
            )
        if party_type == "Employee":
            meta_data = frappe.get_list(
                party_type, fields=["name", "employee_name as party_name"]
            )
        if party_type == "Shareholder":
            meta_data = frappe.get_list(
                party_type, fields=["name", "title as party_name"]
            )
        if party_type == "Supplier":
            meta_data = frappe.get_list(
                party_type, fields=["name", "supplier_name as party_name"]
            )
        gen_response(200, "data get successfully", meta_data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)
