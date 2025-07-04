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


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_active_workflow_document(module=None, internal=False):
    try:
        all_workflows = []
        workflows = frappe.get_all(
            "Workflow", filters={"is_active": 1}, fields=["document_type"]
        )
        if module:
            filtered_workflows = []
            for wf in workflows:
                # Fetch the module of the document_type
                doctype_module = frappe.db.get_value(
                    "DocType", wf["document_type"], "module"
                )

                # Check if module matches the given parameter
                if doctype_module == module:
                    filtered_workflows.append(wf)

            workflows = filtered_workflows  # Update the workflows list

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
    start=1, page_length=10, document_type=None, module=None, internal=False
):
    try:
        # Initialize variables
        all_documents = []
        if document_type == "":
            document_type = "All"
        # Determine the list of doctypes to query
        if document_type in [None, "All"]:
            workflows = get_active_workflow_document(internal=True, module=module)
            workflow_doctypes = [
                row.document_type
                for row in workflows
                if not row.document_type in ["All", None, ""]
            ]
        else:
            workflow_doctypes = [document_type]

        # Fetch documents with pending actions
        workflow_documents = []
        for doctype in workflow_doctypes:
            # Fetch workflow documents with valid transitions
            workflow_document = frappe.get_list(
                doctype,
                filters={
                    "workflow_state": ["!=", None],  # Exclude NULL values
                    "workflow_state": ["!=", ""],  # Exclude empty strings
                },
                fields=[
                    "name",
                    "workflow_state",
                    "modified",
                    f"'{doctype}' as doctype",
                ],
                order_by="modified desc",
            )
            workflow_documents.extend(
                workflow_document
            )  # Add documents to a single list

        # Sort the combined list of documents by 'modified' field in descending order
        workflow_documents = sorted(
            workflow_documents, key=lambda x: x["modified"], reverse=True
        )

        # Apply pagination
        start_index = cint(start) - 1
        end_index = start_index + cint(page_length)
        # Filter only documents with pending actions (transitions)
        temp_start = 0
        for doc in workflow_documents:
            if doc.get("workflow_state"):
                transitions = get_transitions(
                    frappe.get_doc(doc["doctype"], doc["name"])
                )
                if len(transitions) >= 1:
                    all_documents.append(doc)
                    temp_start += 1
            if temp_start == end_index:
                break
        all_documents = all_documents[start_index:end_index]
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
