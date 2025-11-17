import json

import frappe
from frappe.utils import today
from frappe.utils.file_manager import save_file
from employee_self_service.mobile.v1.api_utils import exception_handler, gen_response


@frappe.whitelist()
def create_issue(**data):
    try:
        # Validate required fields
        if not data.get("description"):
            return gen_response(500, "Description are required")

        if not data.get("issue_type"):
            return gen_response(500, "Issue Type is required")

        issue_doc = frappe.new_doc("Pollen Issue")
        issue_doc.description = data.get("description")
        issue_doc.customer = data.get("customer")
        issue_doc.issue_type = data.get("issue_type")
        issue_doc.priority = data.get("priority", "Medium")
        issue_doc.date = today()
        # issue_doc.status = "Open"
        issue_doc.insert(ignore_permissions=True)
        return gen_response(
            200,
            "Pollen Issue created and assigned successfully",
            {
                "issue_id": issue_doc.name,
                "status": issue_doc.status,
                "assigned_to": issue_doc.current_assignee or "Not yet assigned",
                "priority": issue_doc.priority,
                "date": issue_doc.date,
            },
        )

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to perform this action")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def update_issue(**data):
    try:
        issue_id = data.get("issue_id")
        if not issue_id:
            return gen_response(500, "Issue ID is required")

        issue_doc = frappe.get_doc("Pollen Issue", issue_id)

        # Check if user has permission to update
        current_user = frappe.session.user
        if not (
            issue_doc.current_assignee == current_user
            or "System Manager" in frappe.get_roles(current_user)
        ):
            return gen_response(500, "Not permitted to update this issue")

        # Add comment if provided
        if data.get("comment"):
            issue_doc.add_comment("Comment", data.get("comment"))

        # Update other fields if provided
        if data.get("priority"):
            issue_doc.priority = data.get("priority")

        if data.get("description"):
            issue_doc.description = data.get("description")

        # Update status if provided (but not to closed - use separate API for that)
        if data.get("status") and data.get("status") != "Closed":
            issue_doc.status = data.get("status")

        issue_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return gen_response(
            200,
            "Pollen Issue updated successfully",
            {
                "issue_id": issue_doc.name,
                "status": issue_doc.status,
                "priority": issue_doc.priority,
                "current_assignee": issue_doc.current_assignee,
            },
        )

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to update Pollen Issue")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)


@frappe.whitelist()
def get_issue_list(start=0, page_length=10, filters=None, list_type="all"):
    """
    Get list of issues with two types:
    - pending: Issues assigned to current user with status not 'Closed'
    - all: All issues (with optional filters)
    """
    try:
        start = int(start)
        page_length = int(page_length)
        filters = json.loads(filters) if filters else {}
        
        # Ensure filters is always a dictionary
        if not isinstance(filters, dict):
            filters = {}
            
        current_user = frappe.session.user

        # Base fields to fetch
        fields = [
            "name",
            "customer",
            "state",
            "district",
            "issue_type",
            "department",
            "status",
            "current_assignee",
            "date",
            "priority",
            "creation",
            "modified",
        ]

        if list_type == "pending":
            # Get issues assigned to current user that are not closed
            filters.update(
                {"current_assignee": current_user, "status": ["!=", "Closed"]}
            )

        issue_list = frappe.get_list(
            "Pollen Issue",
            fields=fields,
            start=start,
            page_length=page_length,
            order_by="modified desc",
            filters=filters,
        )

        # Add customer name if customer exists
        for issue in issue_list:
            if issue.get("customer"):
                customer_name = frappe.db.get_value(
                    "Customer", issue["customer"], "customer_name"
                )
                issue["customer_name"] = customer_name

        return gen_response(
            200, f"Pollen Issue {list_type} list fetched successfully", issue_list
        )
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read Pollen Issue")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_issue_type_list():
    try:
        issue_types = frappe.get_all("Pollen Issue Type", fields=["name", "issue_type","department"])
        return gen_response(
            200, "Pollen Issue Type list fetched successfully", issue_types
        )
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read Pollen Issue Type")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_issue_priority():
    try:
        issue_priorities = ["High", "Medium", "Low", "Urgent"]
        return gen_response(
            200, "Pollen Issue Priority list fetched successfully", issue_priorities
        )
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read Pollen Issue Priority")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_user_list():
    """Get list of active users for assignment"""
    try:
        users = frappe.get_all(
            "User",
            fields=["name", "full_name", "email"],
            filters={"enabled": 1, "user_type": "System User"},
            order_by="full_name",
        )
        return gen_response(200, "User list fetched successfully", users)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read User")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def update_status(**data):
    """Update issue status with optional comment"""
    try:
        issue_id = data.get("issue_id")
        new_status = data.get("status")
        comment = data.get("comment")

        if not issue_id:
            return gen_response(500, "Issue ID is required")
        if not new_status:
            return gen_response(500, "Status is required")
        frappe.log_error(title="Update Status", message=data)
        # Validate status
        valid_statuses = ["Open", "Closed"]
        if new_status not in valid_statuses:
            return gen_response(
                500, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        issue_doc = frappe.get_doc("Pollen Issue", issue_id)

        # Check permission
        current_user = frappe.session.user
        if not (
            issue_doc.current_assignee == current_user
            or "System Manager" in frappe.get_roles(current_user)
        ):
            return gen_response(500, "Not permitted to update this issue status")

        if new_status == "Closed":
            # Use the close_issue method from the doctype
            result = issue_doc.close_issue(comment)
            if result:
                return gen_response(
                    200,
                    "Issue closed successfully",
                    {
                        "issue_id": issue_doc.name,
                        "status": "Closed",
                        "resolution_date": issue_doc.resolution_date,
                    },
                )
        else:
            # Update status normally
            old_status = issue_doc.status
            issue_doc.status = new_status

            # Add comment if provided
            if comment:
                issue_doc.add_comment(
                    "Comment",
                    f"Status changed from {old_status} to {new_status}. {comment}",
                )

            issue_doc.save()

            return gen_response(
                200,
                "Issue status updated successfully",
                {
                    "issue_id": issue_doc.name,
                    "status": issue_doc.status,
                    "old_status": old_status,
                },
            )

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to update issue status")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def forward_issue(**data):
    """Forward issue to another user"""
    try:
        issue_id = data.get("issue_id")
        to_user = data.get("to_user")
        comment = data.get("comment")

        if not issue_id:
            return gen_response(500, "Issue ID is required")
        if not to_user:
            return gen_response(500, "Target user is required")

        issue_doc = frappe.get_doc("Pollen Issue", issue_id)

        current_user = frappe.session.user
        if to_user == issue_doc.current_assignee:
            return gen_response(500, "Issue is already assigned to this user")

        # Use the forward_issue method from the doctype
        result = issue_doc.forward_issue(to_user, comment)

        if result:
            return gen_response(
                200,
                "Issue forwarded successfully",
                {
                    "issue_id": issue_doc.name,
                    "from_user": current_user,
                    "to_user": to_user,
                    "current_assignee": issue_doc.current_assignee,
                    "status": issue_doc.status,
                },
            )

    except frappe.ValidationError as e:
        return gen_response(500, str(e))
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to forward issue")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def backward_issue(**data):
    """Move issue back to previous assignee"""
    try:
        issue_id = data.get("issue_id")
        comment = data.get("comment")

        if not issue_id:
            return gen_response(500, "Issue ID is required")

        issue_doc = frappe.get_doc("Pollen Issue", issue_id)

        # Use the backward_issue method from the doctype
        result = issue_doc.backward_issue(comment)

        if result:
            return gen_response(
                200,
                "Issue moved back successfully",
                {
                    "issue_id": issue_doc.name,
                    "current_assignee": issue_doc.current_assignee,
                    "status": issue_doc.status,
                },
            )

    except frappe.ValidationError as e:
        return gen_response(500, str(e))
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to move back issue")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def reopen_issue(**data):
    """Reopen a closed issue (System Manager only)"""
    try:
        issue_id = data.get("issue_id")
        comment = data.get("comment")

        if not issue_id:
            return gen_response(500, "Issue ID is required")

        issue_doc = frappe.get_doc("Pollen Issue", issue_id)

        # Check if user is System Manager (only System Managers can reopen)
        current_user = frappe.session.user
        user_roles = frappe.get_roles(current_user)
        if "System Manager" not in user_roles:
            return gen_response(500, "Only System Manager can reopen closed issues")

        # Check if issue is actually closed
        if issue_doc.status != "Closed":
            return gen_response(500, "Issue is not closed")

        # Use the reopen_issue method from the doctype
        result = issue_doc.reopen_issue(comment)

        if result:
            return gen_response(
                200,
                "Issue reopened successfully",
                {
                    "issue_id": issue_doc.name,
                    "status": issue_doc.status,
                    "current_assignee": issue_doc.current_assignee,
                    "resolution_date": None,
                },
            )

    except frappe.ValidationError as e:
        return gen_response(500, str(e))
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to reopen issue")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_assignment_history(issue_id):
    """Get assignment history for an issue"""
    try:
        if not issue_id:
            return gen_response(500, "Issue ID is required")

        # Check if issue exists and user has permission
        if not frappe.db.exists("Pollen Issue", issue_id):
            return gen_response(500, "Issue not found")

        assignment_history = frappe.get_all(
            "Pollen Issue Assignment",
            filters={"parent": issue_id},
            fields=["action", "from_user", "to_user", "note", "timestamp"],
            order_by="timestamp desc",
        )

        # Add user full names
        for assignment in assignment_history:
            if assignment.get("from_user"):
                assignment["from_user_name"] = frappe.db.get_value(
                    "User", assignment["from_user"], "full_name"
                )
            if assignment.get("to_user"):
                assignment["to_user_name"] = frappe.db.get_value(
                    "User", assignment["to_user"], "full_name"
                )

        return gen_response(
            200, "Assignment history fetched successfully", assignment_history
        )

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read assignment history")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_issue_details(**data):
    try:
        issue_doc = frappe.get_doc("Pollen Issue", data.get("name"))
        
        # Get button visibility based on same conditions as JS file
        button_visibility = get_button_visibility(issue_doc)
        
        # Convert document to dict and add button visibility
        issue_data = issue_doc.as_dict()
        issue_data["button_visibility"] = button_visibility
        
        return gen_response(200, "Issue get successfully", issue_data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for read Pollen Issue")
    except Exception as e:
        return exception_handler(e)


def get_button_visibility(issue_doc):
    """
    Determine which buttons should be visible based on the same conditions as JS file
    """
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)
    is_system_manager = "System Manager" in user_roles
    is_current_assignee = issue_doc.current_assignee == current_user
    
    # Check if user has permission to perform actions (current assignee or System Manager)
    can_perform_actions = is_current_assignee or is_system_manager
    
    # Check if issue is not cancelled and not closed
    is_active_issue = issue_doc.docstatus < 2 and issue_doc.status != "Closed"
    
    # Check if there's assignment history for backward button
    has_assignment_history = False
    try:
        if hasattr(issue_doc, 'assignment_history') and issue_doc.assignment_history:
            has_assignment_history = len(issue_doc.assignment_history) > 1
    except (AttributeError, TypeError):
        has_assignment_history = False
    
    button_visibility = {
        "forward": 1 if (is_active_issue and can_perform_actions) else 0,
        "backward": 1 if (is_active_issue and can_perform_actions and has_assignment_history) else 0,
        "close": 1 if (is_active_issue and can_perform_actions) else 0,
        "reopen": 1 if (issue_doc.status == "Closed" and is_system_manager) else 0,
        "can_edit": 1 if not (issue_doc.status == "Closed" and not is_system_manager) else 0
    }
    
    return button_visibility

@frappe.whitelist(allow_guest=True)
def upload_documents(issue_id):
    try:
        if not issue_id or not frappe.db.exists("Pollen Issue", issue_id):
            return gen_response(500, "Invalid or missing Issue ID")

        if "file" not in frappe.request.files:
            return gen_response(500, "Please upload at least one file")

        uploaded_files = []
        files = frappe.request.files.getlist("file")
        for f in files:
            file_doc = save_file(
                fname=f.filename,
                content=f.read(),
                dt="Pollen Issue",
                dn=issue_id,
                is_private=1
            )
            uploaded_files.append({
                "file_name": file_doc.file_name,
                "file_url": file_doc.file_url
            })
        return gen_response(
            200,
            "Files uploaded successfully",
            data=uploaded_files
        )
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)