"""
ESS Workflow API v2
-------------------
Reads list/detail view configuration stored in ESS Workflow Settings and returns
shaped responses that the mobile app can render generically — no hard-coded field
names on the client side.

All endpoints are under:
  /api/method/employee_self_service.mobile.v2.workflow.workflow.<function>
"""

import json

import frappe
from frappe.model.workflow import apply_workflow, get_transitions
from frappe.utils import cint

from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_settings():
    return frappe.get_single("ESS Workflow Settings")


def _parse_config(raw):
    """Safely parse a JSON config string; returns {} on failure."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _default_list_config():
    """Fallback when no list config is stored."""
    return {
        "fields": [
            {"fieldname": "name", "label": "Document No", "fieldtype": "Data", "is_badge": 0},
            {"fieldname": "workflow_state", "label": "Status", "fieldtype": "Data", "is_badge": 1},
            {"fieldname": "modified", "label": "Modified", "fieldtype": "Datetime", "is_badge": 0},
        ]
    }


def _default_detail_config():
    """Fallback when no detail config is stored."""
    return {
        "sections": [
            {
                "label": "Overview",
                "fields": [
                    {"fieldname": "name", "label": "Document No", "fieldtype": "Data", "is_badge": 0},
                    {"fieldname": "workflow_state", "label": "Status", "fieldtype": "Data", "is_badge": 1},
                    {"fieldname": "modified", "label": "Modified", "fieldtype": "Datetime", "is_badge": 0},
                ],
            }
        ]
    }


def _get_doc_config(doctype):
    """Return (list_config, detail_config) for the given doctype from ESS Workflow Settings."""
    settings = _get_settings()
    for row in settings.ess_workflow_documents:
        if row.document == doctype:
            lc = _parse_config(row.list_view_config) or _default_list_config()
            dc = _parse_config(row.detail_view_config) or _default_detail_config()
            return lc, dc
    return _default_list_config(), _default_detail_config()


def _available_actions(doc):
    """Return list of available workflow action strings for the given doc object."""
    try:
        transitions = get_transitions(doc)
        return [t.get("action") for t in transitions if t.get("action")]
    except Exception:
        return []


def _resolve_field_value(doc_dict, fieldname):
    """Get a value from a doc dict; handle nested and missing gracefully."""
    return doc_dict.get(fieldname)


def _build_list_item(doc_dict, doctype, list_config, actions):
    """Shape a single document into the list-view response structure."""
    shaped_fields = []
    for cfg_field in list_config.get("fields", []):
        fname = cfg_field.get("fieldname")
        shaped_fields.append({
            "fieldname": fname,
            "label": cfg_field.get("label", fname),
            "fieldtype": cfg_field.get("fieldtype", "Data"),
            "is_badge": bool(cfg_field.get("is_badge")),
            "value": _resolve_field_value(doc_dict, fname),
        })
    return {
        "name": doc_dict.get("name"),
        "doctype": doctype,
        "workflow_state": doc_dict.get("workflow_state"),
        "fields": shaped_fields,
        "available_actions": actions,
    }


def _build_detail_item(doc_dict, doctype, detail_config, actions):
    """Shape a single document into the detail-view response structure."""
    sections = []
    for section in detail_config.get("sections", []):
        shaped_fields = []
        for cfg_field in section.get("fields", []):
            fname = cfg_field.get("fieldname")
            shaped_fields.append({
                "fieldname": fname,
                "label": cfg_field.get("label", fname),
                "fieldtype": cfg_field.get("fieldtype", "Data"),
                "is_badge": bool(cfg_field.get("is_badge")),
                "value": _resolve_field_value(doc_dict, fname),
            })
        sections.append({"label": section.get("label", ""), "fields": shaped_fields})
    return {
        "name": doc_dict.get("name"),
        "doctype": doctype,
        "workflow_state": doc_dict.get("workflow_state"),
        "available_actions": actions,
        "sections": sections,
    }


def _is_workflow_enabled():
    settings = _get_settings()
    return bool(settings.enable_workflow_in_ess)


def _configured_doctypes():
    settings = _get_settings()
    return [row.document for row in settings.ess_workflow_documents if row.document]


# ── Public API endpoints ───────────────────────────────────────────────────────


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_workflow_doctypes():
    """
    Returns the list of workflow-enabled doctypes configured in ESS Workflow Settings,
    along with the count of documents pending the current user's action.

    Response shape:
    {
        "data": [
            {
                "doctype": "Purchase Order",
                "label": "Purchase Order",
                "pending_count": 5,
                "is_configured": true
            },
            ...
        ]
    }
    """
    try:
        if not _is_workflow_enabled():
            return gen_response(400, "Workflow is not enabled in ESS Settings")

        settings = _get_settings()
        result = []

        for row in settings.ess_workflow_documents:
            if not row.document:
                continue

            lc = _parse_config(row.list_view_config)
            dc = _parse_config(row.detail_view_config)

            # Count docs where current user has at least one available action
            try:
                all_docs = frappe.get_list(
                    row.document,
                    filters={"workflow_state": ["!=", ""]},
                    fields=["name"],
                    ignore_permissions=False,
                )
                pending_count = 0
                for d in all_docs:
                    doc_obj = frappe.get_doc(row.document, d["name"])
                    if _available_actions(doc_obj):
                        pending_count += 1
            except Exception:
                pending_count = 0

            result.append({
                "doctype": row.document,
                "label": row.document,
                "pending_count": pending_count,
                "is_configured": bool(lc and dc),
            })

        return gen_response(200, "Workflow doctypes fetched successfully", result)

    except frappe.PermissionError:
        return gen_response(403, "Not permitted")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_document_list(doctype, start=0, page_length=10, workflow_state=None):
    """
    Returns a paginated list of workflow documents for the given doctype,
    shaped according to the list_view_config stored in ESS Workflow Settings.

    Query params:
      doctype        - e.g. "Purchase Order"
      start          - pagination offset (default 0)
      page_length    - page size (default 10)
      workflow_state - optional filter by state (e.g. "Pending Approval")

    Response shape:
    {
        "data": {
            "doctype": "Purchase Order",
            "total": 12,
            "start": 0,
            "page_length": 10,
            "has_more": true,
            "list_fields": [                         // field schema (for mobile rendering)
                {"fieldname": "name",           "label": "Document No", "fieldtype": "Data",     "is_badge": false},
                {"fieldname": "supplier_name",  "label": "Supplier",    "fieldtype": "Data",     "is_badge": false},
                {"fieldname": "transaction_date","label": "Date",        "fieldtype": "Date",     "is_badge": false},
                {"fieldname": "grand_total",    "label": "Total",       "fieldtype": "Currency", "is_badge": false},
                {"fieldname": "workflow_state", "label": "Status",      "fieldtype": "Data",     "is_badge": true}
            ],
            "documents": [
                {
                    "name": "PUR-ORD-2026-00007",
                    "doctype": "Purchase Order",
                    "workflow_state": "Pending Approval",
                    "fields": [
                        {"fieldname": "name",            "label": "Document No", "fieldtype": "Data",     "is_badge": false, "value": "PUR-ORD-2026-00007"},
                        {"fieldname": "supplier_name",   "label": "Supplier",    "fieldtype": "Data",     "is_badge": false, "value": "TechMart Supplies"},
                        {"fieldname": "transaction_date","label": "Date",        "fieldtype": "Date",     "is_badge": false, "value": "2026-03-12"},
                        {"fieldname": "grand_total",     "label": "Total",       "fieldtype": "Currency", "is_badge": false, "value": 94500.0},
                        {"fieldname": "workflow_state",  "label": "Status",      "fieldtype": "Data",     "is_badge": true,  "value": "Pending Approval"}
                    ],
                    "available_actions": ["Approve", "Reject"]
                }
            ]
        }
    }
    """
    try:
        if not _is_workflow_enabled():
            return gen_response(400, "Workflow is not enabled in ESS Settings")

        if doctype not in _configured_doctypes():
            return gen_response(400, f"'{doctype}' is not configured in ESS Workflow Settings")

        start = cint(start)
        page_length = cint(page_length)

        list_config, _ = _get_doc_config(doctype)
        fetch_fields = list(
            {f["fieldname"] for f in list_config.get("fields", [])} | {"name", "workflow_state"}
        )

        filters = {"workflow_state": ["!=", ""]}
        if workflow_state:
            filters["workflow_state"] = workflow_state

        all_docs = frappe.get_list(
            doctype,
            filters=filters,
            fields=fetch_fields,
            order_by="modified desc",
            ignore_permissions=False,
        )

        # Filter to only docs where the current user has available actions
        actionable = []
        for d in all_docs:
            doc_obj = frappe.get_doc(doctype, d["name"])
            actions = _available_actions(doc_obj)
            if actions:
                d_dict = {k: d.get(k) for k in fetch_fields}
                actionable.append((d_dict, actions))

        total = len(actionable)
        page_slice = actionable[start : start + page_length]

        documents = [
            _build_list_item(d_dict, doctype, list_config, actions)
            for d_dict, actions in page_slice
        ]

        return gen_response(
            200,
            "Document list fetched successfully",
            {
                "doctype": doctype,
                "total": total,
                "start": start,
                "page_length": page_length,
                "has_more": (start + page_length) < total,
                "list_fields": [
                    {
                        "fieldname": f["fieldname"],
                        "label": f.get("label", f["fieldname"]),
                        "fieldtype": f.get("fieldtype", "Data"),
                        "is_badge": bool(f.get("is_badge")),
                    }
                    for f in list_config.get("fields", [])
                ],
                "documents": documents,
            },
        )

    except frappe.PermissionError:
        return gen_response(403, f"Not permitted for {doctype}")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_document_detail(doctype, name):
    """
    Returns a single workflow document shaped by the detail_view_config.

    Response shape:
    {
        "data": {
            "name": "PUR-ORD-2026-00007",
            "doctype": "Purchase Order",
            "workflow_state": "Pending Approval",
            "available_actions": ["Approve", "Reject"],
            "sections": [
                {
                    "label": "Overview",
                    "fields": [
                        {"fieldname": "name",            "label": "Document No", "fieldtype": "Data",     "is_badge": false, "value": "PUR-ORD-2026-00007"},
                        {"fieldname": "workflow_state",  "label": "Status",      "fieldtype": "Data",     "is_badge": true,  "value": "Pending Approval"},
                        {"fieldname": "transaction_date","label": "Date",        "fieldtype": "Date",     "is_badge": false, "value": "2026-03-12"}
                    ]
                },
                {
                    "label": "Financials",
                    "fields": [
                        {"fieldname": "grand_total", "label": "Total Amount", "fieldtype": "Currency", "is_badge": false, "value": 94500.0},
                        {"fieldname": "net_total",   "label": "Net Total",    "fieldtype": "Currency", "is_badge": false, "value": 80000.0}
                    ]
                }
            ]
        }
    }
    """
    try:
        if not _is_workflow_enabled():
            return gen_response(400, "Workflow is not enabled in ESS Settings")

        if doctype not in _configured_doctypes():
            return gen_response(400, f"'{doctype}' is not configured in ESS Workflow Settings")

        _, detail_config = _get_doc_config(doctype)

        # Collect all fieldnames needed across all sections
        detail_fields = {
            f["fieldname"]
            for section in detail_config.get("sections", [])
            for f in section.get("fields", [])
        } | {"name", "workflow_state"}

        doc_obj = frappe.get_doc(doctype, name)
        doc_dict = {fname: doc_obj.get(fname) for fname in detail_fields}

        actions = _available_actions(doc_obj)

        return gen_response(
            200,
            "Document detail fetched successfully",
            _build_detail_item(doc_dict, doctype, detail_config, actions),
        )

    except frappe.DoesNotExistError:
        return gen_response(404, f"{doctype} '{name}' not found")
    except frappe.PermissionError:
        return gen_response(403, f"Not permitted for {doctype}")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_document_actions(doctype, name):
    """
    Returns the list of workflow actions available to the current user for the given document.

    Response shape:
    {
        "data": {
            "doctype": "Purchase Order",
            "name": "PUR-ORD-2026-00007",
            "workflow_state": "Pending Approval",
            "available_actions": ["Approve", "Reject"]
        }
    }
    """
    try:
        doc_obj = frappe.get_doc(doctype, name)
        actions = _available_actions(doc_obj)
        return gen_response(
            200,
            "Document actions fetched successfully",
            {
                "doctype": doctype,
                "name": name,
                "workflow_state": doc_obj.workflow_state,
                "available_actions": actions,
            },
        )
    except frappe.DoesNotExistError:
        return gen_response(404, f"{doctype} '{name}' not found")
    except frappe.PermissionError:
        return gen_response(403, f"Not permitted for {doctype}")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def apply_document_action(doctype, name, action):
    """
    Applies a workflow action (e.g. "Approve", "Reject") to the given document.

    POST body params:
      doctype  - e.g. "Purchase Order"
      name     - document name
      action   - e.g. "Approve"

    Response shape (success):
    {
        "data": {
            "doctype": "Purchase Order",
            "name": "PUR-ORD-2026-00007",
            "workflow_state": "Approved",
            "available_actions": []
        }
    }
    """
    try:
        doc_obj = frappe.get_doc(doctype, name)
        apply_workflow(doc_obj, action)

        # Re-fetch to get updated state
        doc_obj.reload()
        updated_actions = _available_actions(doc_obj)

        return gen_response(
            200,
            f"Action '{action}' applied successfully",
            {
                "doctype": doctype,
                "name": name,
                "workflow_state": doc_obj.workflow_state,
                "available_actions": updated_actions,
            },
        )
    except frappe.DoesNotExistError:
        return gen_response(404, f"{doctype} '{name}' not found")
    except frappe.PermissionError:
        return gen_response(403, f"Not permitted to perform '{action}' on {doctype}")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)
