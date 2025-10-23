import frappe
from frappe import _


@frappe.whitelist()
def get_employee_location(employee, date):
    location_doc = frappe.get_doc(
        "Employee Location", {"employee": employee, "date": date}
    )
    if not location_doc:
        frappe.throw(_("Location details not found for employee"))
    return location_doc.location
