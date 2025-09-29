import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)
from frappe.utils import cint, get_url_to_form, cstr, now_datetime
from operator import itemgetter
from frappe.model.workflow import get_transitions
import json


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
def get_workflow_documents(start=1, page_length=10, document_type=None, internal=False, use_cache=False):
    try:
        # Initialize variables
        all_documents = []
        if document_type == "":
            document_type = "All"
        
        # Check cache for mobile dashboard requests
        cache_key = None
        if use_cache and start == 1 and cint(page_length) <= 10:
            cache_key = f"workflow_docs_{frappe.session.user}_{document_type or 'All'}"
            cached_result = frappe.cache().get_value(cache_key)
            if cached_result:
                try:
                    cached_data = json.loads(cached_result)
                    if internal:
                        return cstr(len(cached_data))
                    return gen_response(
                        200, "Workflow documents fetched successfully (cached)", cached_data
                    )
                except Exception:
                    # Clear invalid cache
                    frappe.cache().delete_value(cache_key)
        
        # Determine the list of doctypes to query
        if document_type in [None, "All"]:
            workflows = get_active_workflow_document(internal=True)
            workflow_doctypes = [
                row.document_type
                for row in workflows
                if not row.document_type in ["All", None, ""]
            ]
        else:
            workflow_doctypes = [document_type]

        # Calculate pagination
        start_index = cint(start) - 1
        required_docs = start_index + cint(page_length)
        
        # Use optimized approach for mobile dashboard (first page with small page_length)
        if start == 1 and cint(page_length) <= 20:
            all_documents = _get_workflow_documents_optimized(workflow_doctypes, required_docs)
        else:
            # Use original approach for list screen with pagination
            all_documents = _get_workflow_documents_full(workflow_doctypes, required_docs)
        
        # Apply final pagination slice
        result_documents = all_documents[start_index:required_docs]
        
        # Cache result for mobile dashboard
        if cache_key and result_documents:
            frappe.cache().set_value(cache_key, json.dumps(result_documents), expires_in_sec=300)  # 5 minutes cache
        
        if internal:
            return cstr(len(result_documents))

        return gen_response(
            200, "Workflow documents fetched successfully", result_documents
        )
    except frappe.PermissionError:
        return gen_response(500, "Not permitted to read document")
    except Exception as e:
        return exception_handler(e)


def _get_workflow_documents_optimized(workflow_doctypes, required_docs):
    """
    Optimized approach for mobile dashboard: fetch documents in small batches
    and check for transitions early to avoid processing unnecessary documents
    """
    all_documents = []
    batch_size = 20  # Process documents in small batches
    max_processed = required_docs * 3  # Safety limit to avoid infinite loops
    processed_count = 0
    
    # Create a list of (doctype, offset) pairs for round-robin fetching
    doctype_offsets = {doctype: 0 for doctype in workflow_doctypes}
    
    while len(all_documents) < required_docs and processed_count < max_processed:
        batch_documents = []
        
        # Fetch a small batch from each doctype
        for doctype in workflow_doctypes:
            if len(all_documents) >= required_docs:
                break
                
            offset = doctype_offsets[doctype]
            
            try:
                workflow_docs = frappe.get_list(
                    doctype,
                    filters={
                        "workflow_state": ["!=", None],
                        "workflow_state": ["!=", ""],
                    },
                    fields=[
                        "name",
                        "workflow_state", 
                        "modified",
                        f"'{doctype}' as doctype",
                    ],
                    order_by="modified desc",
                    start=offset,
                    page_length=batch_size
                )
                
                if not workflow_docs:
                    continue
                    
                batch_documents.extend(workflow_docs)
                doctype_offsets[doctype] += batch_size
                
            except Exception:
                # Skip doctype if there's an error (e.g., permission issues)
                continue
        
        if not batch_documents:
            break
            
        # Sort batch by modified date
        batch_documents.sort(key=lambda x: x["modified"], reverse=True)
        
        # Check for transitions in this batch
        for doc in batch_documents:
            if len(all_documents) >= required_docs:
                break
                
            processed_count += 1
            if doc.get("workflow_state"):
                try:
                    transitions = get_transitions(
                        frappe.get_doc(doc["doctype"], doc["name"])
                    )
                    if transitions:
                        all_documents.append(doc)
                except Exception:
                    # Skip document if there's an error checking transitions
                    continue
    
    return all_documents


def _get_workflow_documents_full(workflow_doctypes, required_docs):
    """
    Original approach for list screen: fetch more documents at once
    """
    workflow_documents = []
    
    for doctype in workflow_doctypes:
        try:
            workflow_document = frappe.get_list(
                doctype,
                filters={
                    "workflow_state": ["!=", None],
                    "workflow_state": ["!=", ""],
                },
                fields=[
                    "name",
                    "workflow_state",
                    "modified", 
                    f"'{doctype}' as doctype",
                ],
                order_by="modified desc",
                page_length=required_docs * 2  # Fetch more to account for filtering
            )
            workflow_documents.extend(workflow_document)
        except Exception:
            continue
    
    # Sort the combined list by 'modified' field in descending order
    workflow_documents = sorted(
        workflow_documents, key=lambda x: x["modified"], reverse=True
    )
    
    # Filter only documents with pending actions (transitions)
    all_documents = []
    for doc in workflow_documents:
        if len(all_documents) >= required_docs:
            break
            
        if doc.get("workflow_state"):
            try:
                transitions = get_transitions(
                    frappe.get_doc(doc["doctype"], doc["name"])
                )
                if transitions:
                    all_documents.append(doc)
            except Exception:
                continue
    
    return all_documents


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
        
        # Clear relevant cache entries
        _clear_workflow_cache()
        
        return gen_response(200, "Workflow State Updated Successfully")
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for update {document_type}")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)


def _clear_workflow_cache():
    """Clear workflow document cache for all users and document types"""
    try:
        # Clear cache patterns for workflow documents
        cache_patterns = [
            f"workflow_docs_{frappe.session.user}_*",
            "workflow_docs_*"
        ]
        
        for pattern in cache_patterns:
            try:
                frappe.cache().delete_keys(pattern)
            except Exception:
                continue
    except Exception:
        # Don't fail the main operation if cache clearing fails
        pass


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
