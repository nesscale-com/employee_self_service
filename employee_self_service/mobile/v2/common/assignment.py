from employee_self_service.mobile.v2.utils import (
    gen_response,
    exception_handler,
    ess_validate,
)
import frappe
from frappe.desk.form import assign_to

@frappe.whitelist()
@ess_validate(methods=["POST"])
def assign_document(
    doctype,
    docname,
    users,
    description=None
):
    try:
        if not frappe.db.exists(doctype, docname):
            return gen_response(404, "Document not found")

        assign_to.add(
            dict(
                assign_to=users,
                doctype=doctype,
                name=docname,
                description=description or "Assigned From Mobile App"
            )
        )
        return gen_response(
            200,
            "Assignment completed successfully"
        )
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_assignments(doctype, docname):
    try:
        assignments = assign_to.get({
            "doctype": doctype,
            "name": docname
        })

        if not assignments:
            return gen_response(
                200,
                "Assignments fetched successfully",
                {
                    "total_assignments": 0,
                    "assignments": []
                }
            )

        users = [d.owner for d in assignments if d.owner]

        user_details = frappe.get_all(
            "User",
            filters={"name": ["in", users]},
            fields=["name", "full_name", "user_image"]
        )

        user_map = {
            user.name: user
            for user in user_details
        }

        for row in assignments:
            user = user_map.get(row.owner)

            row["full_name"] = user.full_name if user else None
            row["user_image"] = user.user_image if user else None

        return gen_response(
            200,
            "Assignments fetched successfully",
            {
                "total_assignments": len(assignments),
                "assignments": assignments
            }
        )

    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def remove_assignment(
    doctype,
    docname,
    user
):
    try:
        assign_to.remove(
            doctype=doctype,
            name=docname,
            assign_to=user
        )
        return gen_response(
            200,
            "Assignment removed successfully"
        )
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def clear_assignments(
    doctype,
    docname
):
    try:
        assign_to.clear(
            doctype,
            docname
        )
        return gen_response(
            200,
            "All assignments cleared successfully"
        )
    except Exception as e:
        return exception_handler(e)