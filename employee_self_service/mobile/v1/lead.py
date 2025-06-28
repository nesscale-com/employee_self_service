import json
import frappe
from frappe import _
from employee_self_service.mobile.v1.api_utils import *
try:
    from erpnext.crm.utils import get_open_activities
except Exception as e:
    pass

@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_lead(**data):
    try:
        lead_doc = frappe.get_doc(doctype="Lead")
        lead_doc.update(data)
        lead_doc.insert()
        return gen_response(200, "Lead created successfully.", lead_doc.name)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for create lead")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_lead_details(name):
    try:
        lead_doc = json.loads(frappe.get_doc("Lead", name).as_json())
        return gen_response(200, "Lead fetched successfully.", lead_doc)
    except frappe.DoesNotExistError:
        return gen_response(404, "Lead not found.")
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to access lead.")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_lead(**data):
    try:
        if not data.get("name"):
            return gen_response(400, "Lead name is required for update.")
        
        lead_doc = frappe.get_doc("Lead", data.get("name"))
        lead_doc.update(data)
        lead_doc.save()
        return gen_response(200, "Lead updated successfully.", lead_doc.name)
    except frappe.DoesNotExistError:
        return gen_response(404, "Lead not found.")
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to update lead.")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def delete_lead(name):
    try:
        frappe.delete_doc("Lead", name)
        return gen_response(200, "Lead deleted successfully.")
    except frappe.DoesNotExistError:
        return gen_response(404, "Lead not found.")
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to delete lead.")
    except Exception as e:
        return exception_handler(e)
    
    
#--------------Lead Dropdown/list APIs----------------#
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_lead_list():
    try:
        leads = frappe.get_all("Lead", 
            filters={"lead_owner":frappe.session.user},
            fields=["name", "lead_owner", "lead_name", "salutation", "first_name","middle_name","last_name","job_title","gender","status","customer","type","request_type","email_id","mobile_no"],
            order_by="creation desc"
        )
        return gen_response(200, "Leads fetched successfully.", leads)
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to list leads.")
    except Exception as e:
        return exception_handler(e)
        
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_options(fieldname):
    try:
        if not fieldname:
            return gen_response(500, "Field name is required to fetch options.")

        meta = frappe.get_meta("Lead")
        options = []
        for df in meta.fields:
            if df.fieldname == fieldname and df.fieldtype == "Select" and df.options:
                options = [
                    {"name": opt.strip()}
                    for opt in df.options.split("\n")
                    if opt.strip()
                ]
                break
        return gen_response(200, "Request type list fetched successfully.", options)
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to list request types.")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_source_list():
    try:
        lead_source = frappe.get_all("Lead Source",fields=["name"])
        return gen_response(200, "Lead source fetched successfully.", lead_source)
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to list lead sources.")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_industry_type_list():
    try:
        industry_type = frappe.get_all("Industry Type",fields=["name"])
        return gen_response(200, "Industry Type list fetched successfully.", industry_type)
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to list Industry Types.")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_country_list():
    try:
        country = frappe.get_all("Country",fields=["name"])
        return gen_response(200, "Country list fetched successfully.", country)
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to list Countries.")
    except Exception as e:
        return exception_handler(e)

#------------ Lead activities APIs -------------------#
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_lead_open_activities(name):
    try:
        open_activities = get_open_activities("Lead", name)
        return gen_response(200, "Lead Open activity list fetched successfully.", open_activities)
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to list Lead Open activities.")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_lead_task(**data):
    try:
        if not data.get("name"):
            return gen_response(500, "Lead name is required for task creation.")
        
        todo = frappe.get_doc({
            "doctype": "ToDo",
            "date": data.get("date") or frappe.utils.now(),
            "allocated_to": data.get("assigned_to"),
            "description": data.get("description"),
            "reference_type": "Lead",
            "reference_name": data.get("name"),
            "priority":"Medium",
            "status": "Open",
        })
        todo.insert()
        return gen_response(200, "Lead Task created successfully.", {"task_name": todo.name})
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to create Lead Task.")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_lead_event(**data):
    try:
        if not data.get("name"):
            return gen_response(500, "Lead name is required for event creation.")
    
        event = frappe.get_doc({
            "doctype": "Event",
            "subject": data.get("subject"),
            "description": data.get("description"),
            "event_category": data.get("event_category"),
            "event_type": data.get("event_type"),
            "starts_on": data.get("date") or frappe.utils.now(),
            "event_participants": [{
                "reference_doctype": "Lead",
                "reference_docname": data.get("name")
            }]
        })
        event.insert()
        return gen_response(200, "Lead event created successfully.", {"event_name": event.name})
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to create Lead Event.")
    except Exception as e:
        return exception_handler(e)
