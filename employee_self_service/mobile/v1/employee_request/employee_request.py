import frappe
import json
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)
from frappe.utils import today

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_request_list(start=0, page_length=20):
    try:
        emp_data = get_employee_by_user(frappe.session.user)

        filters = [["employee", "=", emp_data.name]]

        shift_requests = frappe.get_list(
            "Employee Request Form",
            filters=filters,
            fields=["*"],
            order_by="modified desc",
            start=start,
            page_length=page_length,
        )

        return gen_response(200, "Request Get Successfully", shift_requests)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_request_type_list():
    try:
        request_type_list = frappe.get_all("Employee Request Type", fields=["name"])

        return gen_response(200, "Request Type Get Successfully", request_type_list)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_request_detail(name):
    try:
        emp_data = get_employee_by_user(frappe.session.user)

        if not frappe.db.exists(
            "Employee Request Form", {"name": name, "employee": emp_data.name}
        ):
            return gen_response(403, "Request not found.")

        request_doc = frappe.get_doc("Employee Request Form", name)

        return gen_response(200, "Request get successfully", request_doc)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_employee_request(**data):
    try:
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "image", "department", "company"]
        )

        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        if data.get("name"):
            request_doc = frappe.get_doc("Employee Request Form", data.get("name"))
        else:
            request_doc = frappe.new_doc("Employee Request Form")
        request_doc.employee = emp_data.name
        request_doc.request_type = data.get("request_type")
        request_doc.date = today()
        request_doc.notes = data.get("notes")
        request_doc.save()

        if data.get("name"):
            return gen_response(200, "Employee Request has been updated successfully")
        return gen_response(200, "Employee Request has been created successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to perform this action")
    except Exception as e:
        return exception_handler(e)
