import frappe

from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
    get_employee_by_user,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_shift_request_list(start=0, page_length=20):
    try:
        emp_data = get_employee_by_user(frappe.session.user)

        filters = [["employee", "=", emp_data.name]]

        # Workflow is enabled
        shift_requests = frappe.get_list(
            "Shift Request",
            filters=filters,
            fields=["*"],
            order_by="modified desc",
            start=start,
            page_length=page_length,
        )

        return gen_response(200, "Shift Request Get Successfully", shift_requests)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_shift_request_type_list():
    try:
        shift_type_list = frappe.get_all("Shift Type", fields=["name"])

        return gen_response(200, "Shift Type Get Successfully", shift_type_list)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_shift_request(name):
    try:
        emp_data = get_employee_by_user(frappe.session.user)

        if not frappe.db.exists(
            "Shift Request", {"name": name, "employee": emp_data.name}
        ):
            return gen_response(403, "Shift Request not found.")

        shift_request = frappe.get_doc("Shift Request", name)

        return gen_response(200, "shift request get successfully", shift_request)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_shift_request(**data):
    try:
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "image", "department", "company"]
        )

        if "employee" in data:
            del data["employee"]
        if "status" in data:
            del data["status"]

        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        if data.get("name"):
            shift_request_doc = frappe.get_doc("Shift Request", data.get("name"))
        else:
            shift_request_doc = frappe.new_doc("Shift Request")
        shift_request_doc.employee = emp_data.name
        shift_request_doc.update(data)
        shift_request_doc.save()

        if data.get("name"):
            return gen_response(200, "Shift Request has been updated successfully")
        return gen_response(200, "Shift Reuqest has been created successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to perform this action")
    except Exception as e:
        return exception_handler(e)
