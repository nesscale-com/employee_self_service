import frappe
from frappe import _
from employee_self_service.mobile.v2.utils import (
    gen_response,
    exception_handler,
    get_actions
)
from frappe.permissions import get_doc_permissions

@frappe.whitelist()
def get_ess_doctype_permission(doctype_name, doctype_reference_name):
    """
    API to get current user's permissions and actions for a given document.
    Args:
        doctype_name (str): The DocType name (e.g. "Sales Order").
        doctype_reference_name (str): The document name/ID (e.g. "SO-0001").
    """
    try:
        # Fetch the document
        doc = frappe.get_doc(doctype_name, doctype_reference_name)

        # Get user's permissions
        perms = get_doc_permissions(doc)
        permissions_summary = {
            key: perms.get(key, 0) for key in ("write", "delete", "submit", "cancel")
        }
        if doc.docstatus == 0:
            permissions_summary["cancel"] = 0
        if doc.docstatus == 1:
            permissions_summary["write"] = 0
            permissions_summary["delete"] = 0
            permissions_summary["submit"] = 0
        if doc.docstatus == 2:
            permissions_summary["write"] = 0
            permissions_summary["delete"] = 0
            permissions_summary["submit"] = 0
            permissions_summary["cancel"] = 0

        # Get available actions
        actions = get_actions(doc)
        if len(actions) >= 1:
            permissions_summary["action"] = 1
            permissions_summary["submit"] = 0
            permissions_summary["cancel"] = 0
        else:
            permissions_summary["action"] = 0
        # Success response
        return gen_response(
            200,
            "Permission and actions retrieved successfully",
            {"permissions": permissions_summary, "actions": actions},
        )
    except frappe.PermissionError:
        return gen_response(403, "Not permitted for item")
    except Exception as e:
        return exception_handler(e)