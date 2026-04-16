import frappe
from frappe import _
from employee_self_service.mobile.v1.api_utils import *

def register_device(employee, unique_id):
    ess_settings = get_ess_settings()
    if not ess_settings.get("enable_device_restrictions"):
        return True

    registered_device_id = frappe.db.get_value(
        "Employee Device Registration", {"employee": employee}, "unique_id"
    )

    if not registered_device_id:
        # No existing device, so register the current one
        frappe.get_doc(
            {
                "doctype": "Employee Device Registration",
                "employee": employee,
                "unique_id": unique_id,
            }
        ).insert(ignore_permissions=True)
    elif registered_device_id != unique_id:
        frappe.throw(_("Device not recognized. Please contact admin."))

    return True
