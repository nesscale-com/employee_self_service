import frappe

# from frappe.utils import pretty_date, getdate, fmt_money
from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_directory(start=0, page_length=10, filters=None):
    try:
        current_user = frappe.session.user
        frappe.set_user("Administrator")
        status_filter = ["status", "=", "Active"]
        if filters:
            filters.append(status_filter)
        else:
            filters = [status_filter]
        employee = frappe.get_all(
            "Employee",
            filters=filters,
            fields=[
                "name",
                "employee_name",
                "cell_number",
                "company_email",
                "designation",
                "department",
                "branch",
                "image",
            ],
            start=start,
            page_length=page_length,
        )
        frappe.set_user(current_user)
        return gen_response(200, "Employee list Getting Successfully", employee)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read employee")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_designation_list():
    try:
        current_user = frappe.session.user
        frappe.set_user("Administrator")
        designation_list = frappe.get_all("Designation")
        frappe.set_user(current_user)
        return gen_response(200, "Designation list get successfully", designation_list)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_department_list():
    try:
        current_user = frappe.session.user
        frappe.set_user("Administrator")
        designation_list = frappe.get_all("Department")
        frappe.set_user(current_user)
        return gen_response(200, "Department list get successfully", designation_list)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_branch_list():
    try:
        current_user = frappe.session.user
        frappe.set_user("Administrator")
        designation_list = frappe.get_all("Branch")
        frappe.set_user(current_user)
        return gen_response(200, "Branch list get successfully", designation_list)
    except Exception as e:
        return exception_handler(e)
