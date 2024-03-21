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
from frappe.utils import get_datetime

@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_timesheet(**data):
    try:
        emp_data = get_employee_by_user(
        frappe.session.user, fields=["name", "image", "department","company"]
        )
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        if data.get("name"):
            timesheet_doc = frappe.get_doc("Timesheet",data.get("name"))
        else:
            timesheet_doc = frappe.new_doc("Timesheet")
        timesheet_doc.update(data)
        timesheet_doc.time_logs = []
        timesheet_doc.append("time_logs",data.get("time_logs"))
        timesheet_doc.employee = emp_data.name
        timesheet_doc.company = emp_data.company
        timesheet_doc.save()
        return gen_response(200, "Timesheet has been updated successfully")
    except frappe.PermissionError:
            return gen_response(500, "Not permitted to perform this action")
    except Exception as e:
            return exception_handler(e)
        
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_timesheet_list(start=0, page_length=10, filters=None):
    try:
        timesheet_list = frappe.get_list(
            "Timesheet",
            fields=[
                "*",
            ],
            start=start,
            page_length=page_length,
            order_by="modified desc",
            filters=filters,
        )
        return gen_response(200, "Timesheet List getting Successfully", timesheet_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read Timesheet")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_timesheet_details(**data):
    try:
        timesheet_doc= frappe.get_doc("Timesheet",data.get("name"))
        return gen_response(200, "Timesheet get successfully", timesheet_doc)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for read Timesheet")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_activity_type_list():
    try:
        activity_types = frappe.get_all("Activity Type")
        return gen_response(200, "Activity Type list get successfully", activity_types)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for activity type")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_list(filters=None):
    try:
        task_list = frappe.get_list("Task",filters=filters,fields=["name","subject"])
        return gen_response(200,"Task list get successfully",task_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for read task")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_project_list(start=0, page_length=10, filters=None):
    try:
        project_list = frappe.get_list("Project",filters=filters,fields=["name","project_name"],start=start,
            page_length=page_length,)
        return gen_response(200,"Project list get successfully",project_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for read project")
    except Exception as e:
        return exception_handler(e)