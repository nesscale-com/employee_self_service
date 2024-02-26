import frappe
import json
from frappe import _
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    remove_default_fields,
    get_global_defaults
)


def get_action(doctype,docname,status,row):
    res = _check_workflow(doctype)
    if res:
        from frappe.model.workflow import get_transitions
        row["workflow"] = res
        doc = frappe.get_doc(doctype,docname)
        transitions = get_transitions(doc)
        actions = []
        for row in transitions:
            actions.append(row.get("action"))
        return actions
    else:
        if not status in ["Approved","Rejected"]:
            return ["Approved","Rejected"]
        else:
            return []

def _check_workflow(doctype):
        workflow = frappe.get_all("Workflow",filters={"document_type":doctype,"is_active":1},fields=["name"])
        if workflow:
            return True
        else:
            return False


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_status_list(doctype):
    try:
        status_list = []
        workflow_name = frappe.get_all(
            "Workflow",
            filters={"document_type": doctype, "is_active": 1},
            fields=["name"],
        )
        if workflow_name:
            workflow_states = frappe.get_all(
                "Workflow Document State",
                filters=[["parent", "=", workflow_name]],
                fields=["*"],
            )
            for workflow_state in workflow_states:
                status_list.append(workflow_state.state)
        else:
            payment_entry_meta = frappe.get_meta(doctype)
            status_list = payment_entry_meta.get_field("status").options.split("\n")
            status = []
            for s in status_list:
                if not s in ["Paid","Unpaid",""]:
                    status.append(s)
        return gen_response(200, "status get successfully", status)
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for update {doctype}")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_document_status(doctype,doc_name,status):
    try:
        status_field = get_status_field(doctype)
        doc = frappe.get_doc(doctype,doc_name)
        doc.update({status_field:status})
        doc.submit()
        return gen_response(200,"status updated successfully")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)

def get_status_field(doctype):
    staus_field = "status"
    status_field_map = {
        "Expense Claim":"approval_status"
    }
    if status_field_map.get(doctype):
        status_field =  status_field_map.get(doctype)
    return status_field
