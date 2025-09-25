import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_list(filters=None):
    try:
        employee = get_employee_by_user(frappe.session.user)
        if not employee:
            return gen_response(500, "Employee not found for this user")

        filters = filters or []
        target_list = frappe.get_all(
            "Employee Target Entry",
            filters=(filters + [["employee", "=", employee.get("name")]]),
            fields=[
                "name",
                "target_template",
                "status",
                "ROUND(progress, 2) as progress",
                "frequency",
                "fiscal_year",
                "month",
                "quarter",
                "start_date",
                "end_date",
                "total_target",
                "total_achieved",
            ],
        )

        return gen_response(200, "Employee Targets get successfully", target_list)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_details(target_id=None):
    try:
        if not target_id:
            return gen_response(400, "Target ID is required")

        target_doc = frappe.get_doc("Employee Target Entry", target_id).as_dict()

        return gen_response(200, "Employee Target Details get successfully", target_doc)
    except frappe.PermissionError:
        return gen_response(403, "Unauthorized to access this target")
    except Exception as e:
        return exception_handler(e)
