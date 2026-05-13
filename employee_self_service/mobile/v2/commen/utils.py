import frappe
from frappe import _
from employee_self_service.mobile.v2.utils import *

def get_actions(doc, doc_data=None):
    from frappe.model.workflow import get_transitions

    if not frappe.db.exists(
        "Workflow", dict(document_type=doc.get("doctype"), is_active=1)
    ):
        if doc_data:
            doc_data["workflow_state"] = doc.get("status")
        return []
    try:
        transitions = get_transitions(doc)
    except Exception:
        return []
    actions = []
    for row in transitions:
        actions.append(row.get("action"))
    return actions