import frappe
from frappe.permissions import get_doc_permissions
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    exception_handler,
    get_actions,
)


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


ESS_MENU_DOCTYPE_MAPPING = {
    "Expense": {"name": "Expense Claim", "is_report": 0},
    "Leave": {"name": "Leave Application", "is_report": 0},
    "Payroll": {"name": "Salary Slip", "is_report": 0},
    "Holiday": {"name": "Holiday List", "is_report": 0},
    "Attendance": {"name": "Attendance", "is_report": 0},
    "Transactions": {"name": "General Ledger", "is_report": 1},
    "Order": {"name": "Sales Order", "is_report": 0},
    "Visit": {"name": "Visit", "is_report": 0},
    "Payment": {"name": "Payment Entry", "is_report": 0},
    "Petty Expense": {"name": "Petty Expense", "is_report": 0},
    "Timesheet": {"name": "Timesheet", "is_report": 0},
    "Issue": {"name": "Issue", "is_report": 0},
    "Quotation": {"name": "Quotation", "is_report": 0},
    "Attend Req": {"name": "Attendance Request", "is_report": 0},
    "Shift Req": {"name": "Shift Request", "is_report": 0},
}


def get_user_roles(user):
    """Get all roles of the user."""
    return frappe.get_roles(user)


def get_bulk_doctype_read_permissions(doctype_list, user_roles):
    """
    Bulk fetch DocPerm entries and return a dict of
    {doctype: True} for standard read permissions.
    """
    docperms = frappe.get_all(
        "DocPerm",
        filters={"parent": ["in", doctype_list]},
        fields=["parent", "role", "read"],
    )

    doctype_permissions = {}
    for perm in docperms:
        if perm["read"] == 1 and perm["role"] in user_roles:
            doctype_permissions[perm["parent"]] = True
    return doctype_permissions


def has_report_read_permission(report_name):
    """Check read permission for a report."""
    doc = frappe.get_doc("Report", report_name)
    if doc.is_permitted():
        return True
    else:
        return False


def has_doctype_read_permission(doctype_name):
    """Check read permission for a doctype (includes custom perms)."""
    return frappe.has_permission(doctype_name, "read")


@frappe.whitelist()
def get_ess_menu_visibility():
    """
    Return a dictionary of all menus with a 1/0 flag based on user permissions.
    """
    try:
        user = frappe.session.user

        user_roles = get_user_roles(user)

        doctype_list = [
            details["name"]
            for details in ESS_MENU_DOCTYPE_MAPPING.values()
            if not details["is_report"]
        ]

        doctype_permissions = get_bulk_doctype_read_permissions(
            doctype_list, user_roles
        )

        # Create final dictionary with 1 or 0 flag for each menu
        menu_visibility = {}
        for menu_label, details in ESS_MENU_DOCTYPE_MAPPING.items():
            doctype_or_report = details["name"]
            is_report = details["is_report"]

            if is_report:
                # Reports: fallback to precise
                if has_report_read_permission(doctype_or_report):
                    menu_visibility[menu_label] = 1
                else:
                    menu_visibility[menu_label] = 0
            else:
                # Bulk says YES, skip precise
                if doctype_permissions.get(doctype_or_report):
                    menu_visibility[menu_label] = 1
                else:
                    # Fallback precise check for custom perms
                    if has_doctype_read_permission(doctype_or_report):
                        menu_visibility[menu_label] = 1
                    else:
                        menu_visibility[menu_label] = 0

        return gen_response(
            200,
            "Menu visibility fetched successfully",
            {"menu_visibility": menu_visibility},
        )

    except frappe.PermissionError:
        return gen_response(403, "Not permitted for item")
    except Exception as e:
        return exception_handler(e)
