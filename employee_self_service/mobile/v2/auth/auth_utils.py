import frappe
from frappe import _

def validate_employee(user):
    if not frappe.db.exists("Employee", dict(user_id=user)):
        frappe.throw(_("Please Link Employee with this user"))

def get_employee_by_user(user, fields=["name"]):
    if isinstance(fields, str):
        fields = [fields]
    emp_data = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        fields,
        as_dict=1,
    )
    return emp_data

def get_ess_settings():
    return frappe.get_doc(
        "Employee Self Service Settings", "Employee Self Service Settings"
    )

def get_global_defaults():
    return frappe.get_doc("Global Defaults", "Global Defaults")
