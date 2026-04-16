import frappe
from erpnext.accounts.utils import getdate

from employee_self_service.mobile.v2.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_attendance_request(*args, **kwargs):
    required_fields = ["company", "from_date", "to_date", "reason"]
    data = {
        field: kwargs.get(field)
        for field in required_fields
        + ["half_day", "include_holidays", "shift", "explanation"]
    }
    missing_fields = [field for field in required_fields if not data[field]]

    if missing_fields:
        return gen_response(
            500,
            f"Please provide the following fields to proceed: {', '.join(missing_fields)}.",
        )

    try:
        employee = frappe.get_value(
            "Employee", {"user_id": frappe.session.user}, "name"
        )
        if not employee:
            return gen_response(500, "Employee record not found.")

        if kwargs.get("request_id"):
            request_doc = frappe.get_doc("Attendance Request", kwargs.get("request_id"))
            if request_doc.employee != employee:
                return gen_response(403, "Attendance request not found")

            request_doc.update(data)
            request_doc.save()
            return gen_response(200, "Attendance Request updated successfully.")

        request_doc = frappe.get_doc(
            {"doctype": "Attendance Request", "employee": employee, **data}
        )
        request_doc.insert(ignore_permissions=True)
        return gen_response(200, "Attendance Request created successfully.")

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to manage attendance requests.")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_shift_list():
    try:
        shift_type_list = frappe.get_list("Shift Type", fields=["name"])
        gen_response(200, "Shift Type list get successfully", shift_type_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for shift")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_attendance_request_list(**data):
    try:
        employee = frappe.get_value(
            "Employee", {"user_id": frappe.session.user}, "name"
        )
        if not employee:
            return gen_response(500, "Employee record not found.")

        filters = [["Attendance Request", "employee", "=", employee]]
        if data.get("filters"):
            filters.extend(data.get("filters"))

        attendance_request_list = frappe.get_all(
            "Attendance Request",
            filters=filters,
            fields=[
                "name",
                "employee",
                "employee_name",
                "department",
                "company",
                "from_date",
                "to_date",
                "half_day",
                "half_day_date",
                "include_holidays",
                "shift",
                "reason",
                "explanation",
            ],
        )

        for request in attendance_request_list:
            if request.get("from_date"):
                request["from_date"] = getdate(request["from_date"]).strftime(
                    "%d-%m-%Y"
                )
            if request.get("to_date"):
                request["to_date"] = getdate(request["to_date"]).strftime("%d-%m-%Y")

        return gen_response(
            200,
            "Attendance Request list retrieved successfully.",
            attendance_request_list,
        )
    except frappe.PermissionError as e:
        return gen_response(500, str(e))
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_attendance_request(request_id=None):
    if not request_id:
        return gen_response(500, "Request ID cannot be blank.")

    try:
        employee = frappe.get_value(
            "Employee", {"user_id": frappe.session.user}, "name"
        )
        if not employee:
            return gen_response(500, "Employee record not found.")

        if not frappe.db.exists(
            "Attendance Request", {"name": request_id, "employee": employee}
        ):
            return gen_response(500, "Attendance Request Not found")

        request_doc = frappe.get_value(
            "Attendance Request",
            {"name": request_id, "employee": employee},
            [
                "name",
                "employee",
                "employee_name",
                "department",
                "company",
                "from_date",
                "to_date",
                "half_day",
                "half_day_date",
                "include_holidays",
                "shift",
                "reason",
                "explanation",
            ],
            as_dict=True,
        )
        if request_doc.get("from_date"):
            request_doc["from_date"] = getdate(request_doc["from_date"]).strftime(
                "%d-%m-%Y"
            )
        if request_doc.get("to_date"):
            request_doc["to_date"] = getdate(request_doc["to_date"]).strftime(
                "%d-%m-%Y"
            )
        gen_response(200, "Attendance Request details get successfully.", request_doc)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to access attendance request")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def delete_attendance_request(request_id=None):
    if not request_id:
        return gen_response(500, "Request ID cannot be blank.")
    try:
        frappe.delete_doc("Attendance Request", request_id, force=1)
        return gen_response(200, "Attendance Request deleted successfully.")
    except frappe.PermissionError as e:
        return gen_response(500, str(e))
    except Exception as e:
        return exception_handler(e)
