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
    ess_validate,
    get_employee_by_user,
    validate_employee_data,
    get_ess_settings,
    get_global_defaults,
    exception_handler,
)
from frappe.handler import upload_file


# Expense Claims List
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_expense_claims():
    try:
        global_defaults = get_global_defaults()
        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)
        filters = frappe._dict()
        filters.employee = emp_data.get("name")
        fields = [
            "`tabExpense Claim`.name",
            "`tabExpense Claim`.employee",
            "`tabExpense Claim`.employee_name",
            "`tabExpense Claim`.approval_status",
            "`tabExpense Claim`.status",
            "`tabExpense Claim`.expense_approver",
            "`tabExpense Claim`.total_claimed_amount",
            "`tabExpense Claim`.posting_date",
            "`tabExpense Claim`.company",
            "`tabExpense Claim Detail`.expense_type",
            "count(`tabExpense Claim Detail`.expense_type) as total_expenses",
        ]

        claims = frappe.get_list(
            "Expense Claim",
            fields=fields,
            filters=filters,
            order_by="`tabExpense Claim`.posting_date desc",
            group_by="`tabExpense Claim`.name",
        )
        expense_data = {}
        for expense in claims:
            expense["total_claimed_amount"] = fmt_money(
                expense["total_claimed_amount"],
                currency=global_defaults.get("default_currency"),
            )

            month_year = get_month_year_details(expense)
            expense["posting_date"] = expense.get("posting_date").strftime("%d-%m-%Y")
            if not month_year in list(expense_data.keys())[::-1]:
                expense_data[month_year] = [expense]
            else:
                expense_data[month_year].append(expense)

        return gen_response(200, "Expense date get successfully", expense_data)
    except Exception as e:
        return exception_handler(e)


# Expense Claims List
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_expense_claims_list():
    try:
        global_defaults = get_global_defaults()
        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)
        filters = frappe._dict()
        filters.employee = emp_data.get("name")
        fields = [
            "`tabExpense Claim`.name",
            "`tabExpense Claim`.employee",
            "`tabExpense Claim`.employee_name",
            "`tabExpense Claim`.approval_status",
            "`tabExpense Claim`.status",
            "`tabExpense Claim`.expense_approver",
            "`tabExpense Claim`.total_claimed_amount",
            "`tabExpense Claim`.posting_date",
            "`tabExpense Claim`.company",
            "`tabExpense Claim Detail`.expense_type",
            "`tabExpense Claim Detail`.description",
            "count(`tabExpense Claim Detail`.expense_type) as total_expenses",
        ]

        claims = frappe.get_list(
            "Expense Claim",
            fields=fields,
            filters=filters,
            order_by="`tabExpense Claim`.posting_date desc",
            group_by="`tabExpense Claim`.name",
        )
        expense_data = {"pending": [], "other": []}
        for expense in claims:
            expense["total_claimed_amount"] = fmt_money(
                expense["total_claimed_amount"],
                currency=global_defaults.get("default_currency"),
            )
            if expense.get("status") == "Draft":
                expense_data.get("pending").append(expense)
            else:
                expense_data.get("other").append(expense)

        return gen_response(200, "Expense data get successfully", expense_data)
    except Exception as e:
        return exception_handler(e)


# Helper to get month wise details
def get_month_year_details(expense):
    date = getdate(expense.get("posting_date"))
    month = date.strftime("%B")
    year = date.year
    return f"{month} {year}"


# get totals for expense
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_expense_claim_type_totals():
    try:
        global_defaults = get_global_defaults()
        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)
        filters = frappe._dict()
        filters.employee = emp_data.get("name")
        filters.approval_status = "Approved"
        fields = [
            "`tabExpense Claim`.name",
            "`tabExpense Claim`.employee",
            "`tabExpense Claim`.employee_name",
            "`tabExpense Claim Detail`.expense_type",
            "sum(`tabExpense Claim Detail`.amount) as total_amount",
        ]

        claims = frappe.get_list(
            "Expense Claim",
            fields=fields,
            filters=filters,
            order_by="`tabExpense Claim`.posting_date desc",
            group_by="`tabExpense Claim Detail`.expense_type",
        )

        for claim in claims:
            claim["total_amount_currency"] = fmt_money(
                claim["total_amount"], currency=global_defaults.get("default_currency")
            )

        return gen_response(200, "Expense date get successfully", claims)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_expense_type():
    try:
        expense_types = frappe.get_all(
            "Expense Claim Type", filters={}, fields=["name"]
        )
        return gen_response(200, "Expense type get successfully", expense_types)
    except Exception as e:
        return exception_handler(e)


# create new expense
@frappe.whitelist()
@ess_validate(methods=["POST"])
def apply_expense(**data):
    try:
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "company", "expense_approver"]
        )

        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)

        # expenses=[
        #     {
        #         "expense_date": frappe.form_dict.expense_date,
        #         "expense_type": frappe.form_dict.expense_type,
        #         "description": frappe.form_dict.description,
        #         "amount": frappe.form_dict.amount,
        #     }
        # ],

        payable_account = get_payable_account(emp_data.get("company"))
        expense_doc = frappe.get_doc(
            dict(
                doctype="Expense Claim",
                employee=emp_data.name,
                expense_approver=emp_data.expense_approver,
                posting_date=today(),
                company=emp_data.get("company"),
                payable_account=payable_account,
                items=frappe.form_dict.items,
            )
        )
        expense_doc.update(data)
        expense_doc.insert()

        if data.get("attachments") is not None:
            for file in data.get("attachments"):
                file_doc = frappe.get_doc(
                    {
                        "doctype": "File",
                        "file_url": file.get("file_url"),
                        "attached_to_doctype": "Expense Claim",
                        "attached_to_name": expense_doc.name,
                    }
                )
                file_doc.insert(ignore_permissions=True)

        return gen_response(200, "Expense applied Successfully", expense_doc)
    except Exception as e:
        return exception_handler(e)


# update expense
@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_expense(**data):
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["name", "company"])

        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)

        if not frappe.db.exists(
            "Expense Claim", {"name": data.get("id"), "employee": emp_data.name}
        ):
            return gen_response(500, "Invalid ID")

        expense_doc = frappe.get_doc("Expense Claim", data.get("id"))
        expense_doc.update(data)
        expense_doc.save(ignore_permissions=True)

        if data.get("attachments") is not None:
            for file in data.get("attachments"):
                file_doc = frappe.get_doc(
                    dict(
                        doctype="File",
                        file_url=file.get("file_url"),
                        attached_to_doctype="Expense Claim",
                        attached_to_name=expense_doc.name,
                    )
                ).insert(ignore_permissions=True)

        return gen_response(200, "Expense updated Successfully", expense_doc)
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
def get_expense(*args, **kwargs):
    try:
        data = kwargs
        global_defaults = get_global_defaults()
        expense_doc = json.loads(
            frappe.get_doc("Expense Claim", data.get("id")).as_json()
        )
        for expense_item in expense_doc.get("expenses"):
            expense_item["amount_in_currency"] = fmt_money(
                expense_item.get("amount"),
                currency=global_defaults.get("default_currency"),
            )
            expense_item["section_amount_in_currency"] = fmt_money(
                expense_item.get("sanctioned_amount"),
                currency=global_defaults.get("default_currency"),
            )
        expense_doc["attachments"] = get_attachments(data.get("id"))
        expense_doc["total_claimed_amount"] = fmt_money(
            expense_doc["total_claimed_amount"],
            currency=global_defaults.get("default_currency"),
        )
        expense_doc["total_sanctioned_amount_in_currency"] = fmt_money(
            expense_doc["total_sanctioned_amount"],
            currency=global_defaults.get("default_currency"),
        )
        if expense_doc.get("project"):
            expense_doc["project_name"] = frappe.db.get_value(
                "Project", expense_doc.get("project"), "project_name"
            )
        if expense_doc.get("task"):
            expense_doc["task_name"] = frappe.db.get_value(
                "Task", expense_doc.get("task"), "subject"
            )
        gen_response(200, "Expense detail get successfully.", expense_doc)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Expense")
    except Exception as e:
        return exception_handler(e)


def get_attachments(id):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Expense Claim", "attached_to_name": id},
        fields=["file_url", "file_name"],
    )


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_bull_agreetech_center_list():
    try:
        records = frappe.get_all("Bull Agreetech Center", fields=["name"])
        return gen_response(200, "Bull Agreetech Center records fetched", records)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_sales_outward_list():
    try:
        records = frappe.get_all(
            "Sales Outward",
            fields=["name", "vehicle_no"],
        )
        return gen_response(200, "Sales Outward records fetched", records)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_jams_outward_list():
    try:
        records = frappe.get_all("JAMS Outward", fields=["name", "employee"])
        return gen_response(200, "JAMS Outward records fetched", records)
    except Exception as e:
        return exception_handler(e)
