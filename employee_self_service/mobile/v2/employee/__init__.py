import frappe
from frappe import _
from employee_self_service.mobile.v1.employee.salary_slip import *
from employee_self_service.mobile.v1.employee.checkin import *
from employee_self_service.mobile.v1.employee.utils import *


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_profile_picture():
    try:
        emp_data = get_employee_by_user(frappe.session.user)

        employee_profile_picture = upload_file()
        employee_profile_picture.attached_to_doctype = "Employee"
        employee_profile_picture.attached_to_name = emp_data.get("name")
        employee_profile_picture.attached_to_field = "image"
        employee_profile_picture.save(ignore_permissions=True)

        frappe.db.set_value(
            "Employee", emp_data.get("name"), "image", employee_profile_picture.file_url
        )
        if employee_profile_picture:
            frappe.db.set_value(
                "User",
                frappe.session.user,
                "user_image",
                employee_profile_picture.file_url,
            )
        return gen_response(200, "Employee profile picture updated successfully")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_profile_detail_tabs():
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        emp_doc = frappe.get_doc("Employee", emp_data.get("name"))
        response = {}

        personal_details = {}
        personal_details["date_of_birth"] = emp_doc.date_of_birth
        personal_details["personal_email"] = emp_doc.personal_email
        personal_details["gender"] = emp_doc.gender
        personal_details["cell_number"] = emp_doc.cell_number
        personal_details["current_address"] = emp_doc.current_address
        personal_details["person_to_be_contacted"] = emp_doc.person_to_be_contacted
        personal_details["emergency_phone_number"] = emp_doc.emergency_phone_number
        response["personal_details"] = personal_details

        education_details = {}
        education_details["education"] = emp_doc.education
        response["education_details"] = education_details

        bank_details = {}
        bank_details["bank_name"] = emp_doc.get("bank_name") or ""
        bank_details["bank_ac_no"] = emp_doc.get("bank_ac_no") or ""
        bank_details["iban"] = emp_doc.get("iban") or ""
        response["bank_details"] = bank_details
        return gen_response(200, "Profile Details get successfully", response)
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_profile():
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        employee_details = frappe.get_cached_value(
            "Employee",
            emp_data.get("name"),
            [
                "employee_name",
                "designation",
                "name",
                "date_of_joining",
                "date_of_birth",
                "gender",
                "company_email",
                "personal_email",
                "cell_number",
                "emergency_phone_number",
            ],
            as_dict=True,
        )
        employee_details["date_of_joining"] = employee_details[
            "date_of_joining"
        ].strftime("%d-%m-%Y")
        employee_details["date_of_birth"] = employee_details["date_of_birth"].strftime(
            "%d-%m-%Y"
        )

        employee_details["employee_image"] = frappe.get_cached_value(
            "Employee", emp_data.get("name"), "image"
        )

        return gen_response(200, "Profile get successfully", employee_details)
    except Exception as e:
        return exception_handler(e)
