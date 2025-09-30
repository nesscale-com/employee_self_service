import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_ess_custom_fields(doctype_name):
    try:
        if not frappe.db.exists("ESS Custom Field", doctype_name):
            return gen_response(200, "No custom fields found for this form", [])
        custom_field_doc = frappe.get_doc("ESS Custom Field", doctype_name)
        return gen_response(
            200, "Custom fields retrieved successfully", custom_field_doc
        )
    except Exception as e:
        return exception_handler(e)
