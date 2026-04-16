import frappe
from frappe import _

from employee_self_service.mobile.v2.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
    get_employee_by_user,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_hr_settings():
    try:
        settings = frappe.get_doc("HR Settings", "HR Settings")
        return gen_response(200, "HR settings get successfully", settings)
    except Exception as e:
        return exception_handler(e)
