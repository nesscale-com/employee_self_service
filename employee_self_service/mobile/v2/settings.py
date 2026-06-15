import frappe
from frappe import _
from employee_self_service.mobile.v2.utils import (
    gen_response,
    exception_handler,
    ess_validate,
    remove_default_fields,
)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_field_staff_settings():
    try:
        settings = frappe.get_single("ESS Field Staff Settings")
        return gen_response(
            200,
            "Field Staff Settings fetched successfully",
            remove_default_fields(settings.as_dict()),
        )
    except Exception as e:
        return exception_handler(e)