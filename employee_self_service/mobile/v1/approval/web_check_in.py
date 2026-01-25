import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)
from frappe.utils import cint, get_url_to_form, cstr
from operator import itemgetter
from frappe.model.workflow import get_transitions


def apply_list_type_filters(doctype, list_type):
    """
    Apply list_type specific filters based on doctype.

    Args:
        doctype: The DocType to filter
        list_type: Filter type - "pending" or "history"

    Returns:
        list: Filter condition to append, or None if no filter applies
    """
    if not list_type:
        return None

    # Employee Request Form filters
    if doctype == "Employee Request Form":
        if list_type == "pending":
            return [
                "Employee Request Form",
                "workflow_state",
                "in",
                ["Under Review", "Approved By CEO", "Approved By HR", "In Process"],
            ]
        elif list_type == "history":
            return [
                "Employee Request Form",
                "workflow_state",
                "in",
                ["Completed", "Rejected"],
            ]

    # Leave Application filters
    elif doctype == "Leave Application":
        if list_type == "pending":
            return [
                "Leave Application",
                "workflow_state",
                "in",
                ["Pending Line Manager Approval", "Pending CEO Approval"],
            ]
        elif list_type == "history":
            return [
                "Leave Application",
                "workflow_state",
                "in",
                ["Approved", "Rejected", "Cancelled"],
            ]

    # Web Check in filters
    elif doctype == "Web Check in":
        if list_type == "pending":
            return ["Web Check in", "workflow_state", "=", "Pending"]
        elif list_type == "history":
            return ["Web Check in", "workflow_state", "!=", "Pending"]

    return None


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_doctype_workflow_documents(
    doctype=None, fields=None, filters=None, start=0, page_length=10, list_type=None
):
    """
    Get documents that have pending workflow transitions for the current user.

    Args:
        doctype: The DocType to fetch documents for (e.g., "Web Check in")
        fields: Comma-separated string or list of fields to fetch (e.g., "name,workflow_state,modified")
        filters: List of filters from mobile side in format [["field", "operator", "value"]] or dict
        start: Starting index for pagination
        page_length: Number of documents to fetch
        list_type: Filter type - "pending" or "history" (optional)
    """
    try:
        if not doctype:
            return gen_response(400, "doctype parameter is required", [])

        start = cint(start)
        page_length = cint(page_length)
        start_index = start

        # Start with default fields
        fields_list = ["name", "workflow_state", "modified"]

        # Append additional fields from parameter
        if fields:
            if isinstance(fields, str):
                additional_fields = [f.strip() for f in fields.split(",")]
            else:
                additional_fields = fields

            # Add additional fields, avoiding duplicates
            for field in additional_fields:
                if field not in fields_list:
                    fields_list.append(field)

        # Verify workflow is active for the doctype
        workflow_exists = frappe.db.exists(
            "Workflow", {"document_type": doctype, "is_active": 1}
        )

        if not workflow_exists:
            return gen_response(200, f"No active workflow configured for {doctype}", [])

        # Build filters
        query_filters = [[doctype, "workflow_state", "!=", ""]]

        # Merge additional filters if provided
        if filters:
            if isinstance(filters, str):
                import json

                filters = json.loads(filters)

            if isinstance(filters, dict):
                # Convert dict to list format
                for key, value in filters.items():
                    if isinstance(value, list) and len(value) == 2:
                        query_filters.append([doctype, key, value[0], value[1]])
                    else:
                        query_filters.append([doctype, key, "=", value])
            elif isinstance(filters, list):
                query_filters.extend(filters)

        # Apply list_type filters based on doctype
        list_type_filter = apply_list_type_filters(doctype, list_type)
        if list_type_filter:
            query_filters.append(list_type_filter)

        # Get only documents with workflow_state
        workflow_documents = frappe.get_list(
            doctype,
            filters=query_filters,
            fields=fields_list,
            order_by="modified desc",
        )

        all_documents = []
        collected_count = 0
        scanned_count = 0

        for doc in workflow_documents:
            # For history list type, include all documents without checking transitions
            # For pending or default, only include documents with available transitions
            if list_type == "history":
                should_include = True
            else:
                transitions = get_transitions(frappe.get_doc(doctype, doc["name"]))
                should_include = bool(transitions)
            
            if should_include:
                if scanned_count >= start_index and collected_count < page_length:
                    doc["doctype"] = doctype

                    # If employee field exists, fetch employee_name
                    if "employee" in fields_list and doc.get("employee"):
                        employee_name = frappe.db.get_value(
                            "Employee", doc["employee"], "employee_name"
                        )
                        if employee_name:
                            doc["employee_name"] = employee_name

                    all_documents.append(doc)
                    collected_count += 1
                scanned_count += 1

            if collected_count >= page_length:
                break

        return gen_response(
            200, f"{doctype} documents fetched successfully", all_documents
        )

    except frappe.PermissionError:
        return gen_response(500, f"Not permitted to read {doctype} documents")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_workflow_document_details(doctype=None, name=None):
    """
    Get complete details of a specific document for approval.

    Args:
        doctype: The DocType of the document (e.g., "Web Check in")
        name: The name/ID of the document (e.g., "WCI-00001")
    """
    try:
        if not doctype:
            return gen_response(400, "doctype parameter is required", {})

        if not name:
            return gen_response(400, "name parameter is required", {})

        # Check if document exists
        if not frappe.db.exists(doctype, name):
            return gen_response(404, f"{doctype} {name} not found", {})

        # Get the complete document
        doc = frappe.get_doc(doctype, name)

        # Convert to dict to return
        doc_dict = doc.as_dict()

        if doc_dict["employee"]:
            employee_name = frappe.db.get_value(
                "Employee", doc_dict["employee"], "employee_name"
            )
            if employee_name:
                doc_dict["employee_name"] = employee_name

        # Get available workflow transitions for this document
        transitions = get_transitions(doc)
        doc_dict["available_transitions"] = transitions if transitions else []

        return gen_response(200, f"{doctype} details fetched successfully", doc_dict)

    except frappe.PermissionError:
        return gen_response(403, f"Not permitted to read {doctype} {name}", {})
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_active_workflow_document(module=None, internal=False):
    try:
        all_workflows = []
        workflow_filters = {}
        if module:
            workflow_filters = {"module": module}

        defined_workflows = frappe.get_all(
            "ESS Workflow Setting Details",
            filters=workflow_filters,
            fields=["workflow"],
            pluck="workflow",
        )

        workflows = frappe.get_all(
            "Workflow",
            filters=[
                ["Workflow", "is_active", "=", 1],
                ["Workflow", "name", "in", defined_workflows],
            ],
            fields=["document_type"],
        )

        # filtered_workflows = []
        # for wf in workflows:
        #     # Fetch the module of the document_type
        #     doctype_module = frappe.db.get_value(
        #         "DocType", wf["document_type"], "module"
        #     )

        #     # Check if module matches the given parameter
        #     if doctype_module == module:
        #         filtered_workflows.append(wf)
        # workflows = filtered_workflows  # Update the workflows list

        if internal:
            return workflows
        all_workflows.append({"document_type": "All"})
        all_workflows.extend(workflows)
        return gen_response(
            200, "Active Workflow document get successfully", all_workflows
        )
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read Timesheet")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_workflow_documents(
    start=0, page_length=10, document_type=None, module=None, internal=False
):
    try:
        start = cint(start)
        page_length = cint(page_length)
        start_index = start
        # start_index = start + 1
        end_index = start + page_length

        if document_type == "":
            document_type = "All"

        if document_type in [None, "All"]:
            workflows = get_active_workflow_document(internal=True, module=module)
            workflow_doctypes = [
                row.document_type
                for row in workflows
                if row.document_type not in ["All", None, ""]
            ]
        else:
            workflow_doctypes = [document_type]

        all_documents = []
        collected_count = 0
        scanned_count = 0

        for doctype in workflow_doctypes:
            # Get only documents with workflow_state
            workflow_documents = frappe.get_list(
                doctype,
                filters={
                    "workflow_state": ["!=", ""],
                },
                fields=[
                    "name",
                    "workflow_state",
                    "modified",
                    f"'{doctype}' as doctype",
                ],
                order_by="modified desc",
            )

            for doc in workflow_documents:
                # Skip until reaching the start_index for valid ones
                transitions = get_transitions(
                    frappe.get_doc(doc["doctype"], doc["name"])
                )
                if transitions:
                    if scanned_count >= start_index and collected_count < page_length:
                        all_documents.append(doc)
                        collected_count += 1
                    scanned_count += 1

                if collected_count >= page_length:
                    break
            if collected_count >= page_length:
                break

        if internal:
            return len(all_documents)

        return gen_response(
            200, "Workflow documents fetched successfully", all_documents
        )

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read document")
    except Exception as e:
        return exception_handler(e)


# def append_document(workflow_documents, documents, doctype):
#     for row in workflow_documents:
#         doc = frappe.get_doc(doctype, row["name"])
#         try:
#             transitions = get_transitions(doc)
#             # Only append documents that have available actions (transitions)
#             if transitions:
#                 row["doctype"] = doctype
#                 documents.append(row)
#         except Exception as e:
#             pass


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_actions(document_type, document_no):
    try:
        doc = frappe.get_doc(document_type, document_no)

        transitions = get_transitions(doc)
        actions = []
        for row in transitions:
            actions.append(row.get("action"))
        return gen_response(200, "Document action list get successfully", actions)
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for action")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_workflow_state(document_type, document_no, action):
    try:
        from frappe.model.workflow import apply_workflow

        doc = frappe.get_doc(document_type, document_no)
        apply_workflow(doc, action)
        return gen_response(200, "Workflow State Updated Successfully")
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for update {document_type}")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_erp_link_for_document(document_type, document_no):
    try:
        return gen_response(
            200,
            "Document link get successfully",
            get_url_to_form(document_type, document_no),
        )
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_print(document_type, document_no):
    try:
        default_print_format = (
            frappe.db.get_value(
                "Property Setter",
                dict(property="default_print_format", doc_type=document_type),
                "value",
            )
            or "Standard"
        )
        from frappe.utils.print_format import download_pdf

        return download_pdf(
            doctype=document_type,
            name=document_no,
            format=default_print_format,
        )
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_all_employees(filters=None, fields=None):
    """
    Get list of all employees.

    Args:
        filters: List of filters in format [["field", "operator", "value"]] or dict
        fields: Comma-separated string or list of fields to fetch (e.g., "name,employee_name,department")
    """
    try:
        # Default fields
        fields_list = ["name", "employee_name", "status"]

        # Append additional fields from parameter
        if fields:
            if isinstance(fields, str):
                additional_fields = [f.strip() for f in fields.split(",")]
            else:
                additional_fields = fields

            # Add additional fields, avoiding duplicates
            for field in additional_fields:
                if field not in fields_list:
                    fields_list.append(field)

        # Build filters
        query_filters = {}

        # Merge additional filters if provided
        if filters:
            if isinstance(filters, str):
                import json

                filters = json.loads(filters)

            if isinstance(filters, dict):
                query_filters = filters
            elif isinstance(filters, list):
                query_filters = filters

        # Get employees
        employees = frappe.get_list(
            "Employee",
            filters=query_filters,
            fields=fields_list,
            order_by="employee_name asc",
        )

        return gen_response(200, "Employees fetched successfully", employees)

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read Employee")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_reportees(fields=None):
    """
    Get list of employees who report to the current logged in employee.
    This includes employees where:
    1. Current employee is set in 'reports_to' field
    2. Current user is set in 'leave_approver' field
    3. Current user is set in 'expense_approver' field

    Args:
        fields: Comma-separated string or list of fields to fetch (e.g., "name,employee_name,department")
    """
    try:
        # Get current user
        current_user = frappe.session.user

        # Get current employee
        current_employee = get_employee_by_user(current_user)
        if not current_employee:
            return gen_response(400, "No employee record found for current user", [])

        # Default fields
        fields_list = ["name", "employee_name", "status", "department"]

        # Append additional fields from parameter
        if fields:
            if isinstance(fields, str):
                additional_fields = [f.strip() for f in fields.split(",")]
            else:
                additional_fields = fields

            # Add additional fields, avoiding duplicates
            for field in additional_fields:
                if field not in fields_list:
                    fields_list.append(field)

        # Get employees reporting to current employee (reports_to field)
        reportees_by_hierarchy = frappe.get_all(
            "Employee",
            filters={"reports_to": current_employee},
            fields=fields_list,
        )

        # Get employees where current user is leave_approver
        reportees_by_leave_approver = frappe.get_all(
            "Employee",
            filters={"leave_approver": current_user},
            fields=fields_list,
        )

        # Get employees where current user is expense_approver
        reportees_by_expense_approver = frappe.get_all(
            "Employee",
            filters={"expense_approver": current_user},
            fields=fields_list,
        )

        # Combine all lists and remove duplicates
        all_reportees = {}
        for emp in (
            reportees_by_hierarchy
            + reportees_by_leave_approver
            + reportees_by_expense_approver
        ):
            all_reportees[emp["name"]] = emp

        # Convert back to list and sort by employee_name
        reportees_list = sorted(
            all_reportees.values(), key=lambda x: x.get("employee_name", "")
        )

        return gen_response(200, "Reportees fetched successfully", reportees_list)

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read Employee")
    except Exception as e:
        return exception_handler(e)
