import frappe 
from frappe import _
from employee_self_service.mobile.v2.employee.utils import *
from frappe.handler import upload_file

@frappe.whitelist()
def create_employee_log(
    log_type, log_time=None, location=None, odometer_reading=None, attendance_image=None
):
    try:
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "default_shift", "branch"]
        )
        log_doc = frappe.get_doc(
            doctype="Employee Checkin",
            employee=emp_data.get("name"),
            log_type=log_type,
            time=log_time if log_time else now_datetime().__str__()[:-7],
            location=location,
            odometer_reading=odometer_reading,
        ).insert(ignore_permissions=True)

        if "file" in frappe.request.files:
            file = upload_file()
            file.attached_to_doctype = "Employee Checkin"
            file.attached_to_name = log_doc.name
            file.attached_to_field = "attendance_image"
            file.save(ignore_permissions=True)
            log_doc.attendance_image = file.get("file_url")
            log_doc.save(ignore_permissions=True)

        update_shift_last_sync(emp_data)
        return gen_response(200, "Employee log added")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def create_out_location_checkout(out_time, reason, location=None):
    try:
        emp_data = get_employee_by_user(
            frappe.session.user, fields=["name", "default_shift", "branch"]
        )

        log_doc = frappe.get_doc(
            doctype="Employee Checkin",
            employee=emp_data.get("name"),
            log_type="OUT",
            time=out_time,
            location=location,
            out_of_location_checkout=1,
            out_of_location_checkout_reason=reason,
        ).insert(ignore_permissions=True)

        if "file" in frappe.request.files:
            file = upload_file()
            file.attached_to_doctype = "Employee Checkin"
            file.attached_to_name = log_doc.name
            file.attached_to_field = "attendance_image"
            file.save(ignore_permissions=True)
            log_doc.attendance_image = file.get("file_url")
            log_doc.save(ignore_permissions=True)

        update_shift_last_sync(emp_data)
        return gen_response(200, "Employee log added")
    except Exception as e:
        return exception_handler(e)
