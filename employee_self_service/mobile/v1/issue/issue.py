import frappe
import json
from frappe import _
# from frappe.utils import pretty_date, getdate, fmt_money
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create(**data):
    try:
        emp_data = get_employee_by_user(
        frappe.session.user, fields=["name", "image", "department","company"]
        )
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        if data.get("name"):
            issue_doc = frappe.get_doc("Issue",data.get("name"))
        else:
            issue_doc = frappe.new_doc("Issue")
        issue_doc.update(data)
        issue_doc.raised_by = frappe.session.user
        issue_doc.save()
        return gen_response(200, "Issue has been created successfully")
    except frappe.PermissionError:
            return gen_response(500, "Not permitted to perform this action")
    except Exception as e:
            return exception_handler(e)
        
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_issue_list(start=0, page_length=10, filters=None):
    try:
        issue_list = frappe.get_list(
            "Issue",
            fields=[
                "*",
            ],
            start=start,
            page_length=page_length,
            order_by="modified desc",
            filters=filters,
        )
        return gen_response(200, "Issue List getting Successfully", issue_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read Issue")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_issue_details(**data):
    try:
        issue_doc= frappe.get_doc("Issue",data.get("name"))
        return gen_response(200, "Issue get successfully", issue_doc)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for read Issue")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_issue_type_list():
    try:
        activity_types = frappe.get_all("Issue Type")
        return gen_response(200, "Issue Type list get successfully", activity_types)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for activity type")
    except Exception as e:
        return exception_handler(e)
    

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_issue_priority():
    try:
        priority_list = frappe.get_all("Issue Priority")
        return gen_response(200, "Issue Priority list get successfully", priority_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for activity type")
    except Exception as e:
        return exception_handler(e)