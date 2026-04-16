import frappe
from frappe.model.workflow import get_transitions
from frappe.utils import cint, get_url_to_form

from employee_self_service.mobile.v2.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
)
from employee_self_service.mobile.v2.commen import get_print, get_erp_link_for_document


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_active_workflow_document(internal=False):
    try:
        all_workflows = []
        workflows = frappe.get_all(
            "Workflow", filters={"is_active": 1}, fields=["document_type"]
        )
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
def get_workflow_documents(start=1, page_length=10, document_type=None, internal=False):
    try:
        start = cint(start)
        page_length = cint(page_length)
        start_index = start
        start + page_length

        if document_type == "":
            document_type = "All"

        if document_type in [None, "All"]:
            workflows = get_active_workflow_document(internal=True)
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
        return gen_response(500, "Not permitted for action")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_workflow_state(reference_doctype, reference_name, action):
    try:
        from frappe.model.workflow import apply_workflow

        doc = frappe.get_doc(reference_doctype, reference_name)
        apply_workflow(doc, action)
        return gen_response(200, "Workflow State Updated Successfully")
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for update {reference_doctype}")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)
