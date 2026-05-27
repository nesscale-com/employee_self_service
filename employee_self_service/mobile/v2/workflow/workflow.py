"""
ESS Workflow API v2 — Flutter-ready endpoints.

All presentation config (Flutter type map, badge colours, action styles,
default list/detail configs) lives in `ess_workflow_settings`.
"""

import frappe
from frappe.model.workflow import apply_workflow, get_transitions
from frappe.utils import cint, fmt_money, formatdate, format_datetime

from employee_self_service.employee_self_service.doctype.ess_workflow_settings.ess_workflow_settings import (
    action_descriptor,
    badge_color,
    configured_doctypes,
    flutter_type,
    get_doc_config,
    is_enabled,
)
from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
)


# ── Formatting ────────────────────────────────────────────────────────────────

def _default_currency():
    return frappe.db.get_single_value("Global Defaults", "default_currency") or "INR"


def _fmt(raw, fieldtype, currency=None):
    if raw is None:
        return {"value": "", "raw": None}

    try:
        if fieldtype == "Currency":
            return {"value": fmt_money(raw, currency=currency or _default_currency()), "raw": float(raw)}
        if fieldtype == "Date":
            return {"value": formatdate(str(raw), "dd MMM yyyy"), "raw": str(raw)}
        if fieldtype == "Datetime":
            return {"value": format_datetime(str(raw), "dd MMM yyyy, hh:mm a"), "raw": str(raw)}
        if fieldtype == "Check":
            return {"value": "Yes" if raw else "No", "raw": bool(raw)}
        if fieldtype == "Percent":
            return {"value": f"{raw}%", "raw": raw}
    except Exception:
        return {"value": str(raw), "raw": raw}

    return {"value": str(raw), "raw": raw}


def _shape_field(cfg, raw_value, currency=None):
    fname = cfg.get("fieldname", "")
    ftype = cfg.get("fieldtype", "Data")
    is_badge = bool(cfg.get("is_badge"))
    slot = cfg.get("slot") or ("status" if is_badge else "body")

    descriptor = {
        "fieldname": fname,
        "label":     cfg.get("label") or fname,
        "type":      flutter_type(ftype, is_badge),
        "is_badge":  is_badge,
        "slot":      slot,
        **_fmt(raw_value, ftype, currency),
    }
    if is_badge:
        descriptor["badge"] = badge_color(descriptor["value"] or str(raw_value or ""))
    return descriptor


def _doc_currency(doc):
    return getattr(doc, "currency", None) or _default_currency()


def _available_actions(doc):
    try:
        return [t.get("action") for t in get_transitions(doc) if t.get("action")]
    except Exception:
        return []


def _shape_actions(action_names):
    return [action_descriptor(a) for a in action_names]


def _ensure_doctype_configured(doctype):
    if not is_enabled():
        return gen_response(400, "Workflow is not enabled in ESS Settings")
    if doctype not in configured_doctypes():
        return gen_response(400, f"'{doctype}' is not configured in ESS Workflow Settings")
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_workflow_doctypes():
    """Home screen — configured doctypes + pending counts for current user."""
    try:
        if not is_enabled():
            return gen_response(400, "Workflow is not enabled in ESS Settings")

        from employee_self_service.employee_self_service.doctype.ess_workflow_settings.ess_workflow_settings import (
            get_settings,
        )

        result = []
        for row in get_settings().ess_workflow_documents:
            if not row.document:
                continue
            try:
                docs = frappe.get_list(row.document, filters={"workflow_state": ["!=", ""]}, pluck="name")
                pending = sum(1 for n in docs if _available_actions(frappe.get_doc(row.document, n)))
            except Exception:
                pending = 0
            result.append({
                "doctype":       row.document,
                "label":         row.document,
                "pending_count": pending,
                "is_configured": True,
            })
        return gen_response(200, "Workflow doctypes fetched successfully", result)

    except frappe.PermissionError:
        return gen_response(403, "Not permitted")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_document_list(doctype, start=0, page_length=10, workflow_state=None):
    """List screen — paginated documents shaped by list_view_config."""
    try:
        err = _ensure_doctype_configured(doctype)
        if err:
            return err

        start, page_length = cint(start), cint(page_length)
        list_config, _ = get_doc_config(doctype)
        list_fields = list_config.get("fields", [])

        fetch_fields = list(
            {f["fieldname"] for f in list_fields} | {"name", "workflow_state", "currency"}
        )

        filters = {"workflow_state": ["!=", ""]}
        if workflow_state:
            filters["workflow_state"] = workflow_state

        rows = frappe.get_list(doctype, filters=filters, fields=fetch_fields, order_by="modified desc")

        actionable = []
        for r in rows:
            doc = frappe.get_doc(doctype, r["name"])
            acts = _available_actions(doc)
            if acts:
                actionable.append((dict(r), acts, _doc_currency(doc)))

        total = len(actionable)
        page = actionable[start : start + page_length]

        schema = [{
            "fieldname": f["fieldname"],
            "label":     f.get("label", f["fieldname"]),
            "type":      flutter_type(f.get("fieldtype", "Data"), bool(f.get("is_badge"))),
            "is_badge":  bool(f.get("is_badge")),
            "slot":      f.get("slot") or ("status" if f.get("is_badge") else "body"),
        } for f in list_fields]

        documents = []
        for data, acts, cur in page:
            state = data.get("workflow_state") or ""
            documents.append({
                "name":              data.get("name"),
                "doctype":           doctype,
                "workflow_state":    state,
                "badge":             badge_color(state),
                "fields":            [_shape_field(cfg, data.get(cfg.get("fieldname")), cur) for cfg in list_fields],
                "available_actions": _shape_actions(acts),
            })

        return gen_response(200, "Document list fetched successfully", {
            "doctype":     doctype,
            "total":       total,
            "start":       start,
            "page_length": page_length,
            "has_more":    (start + page_length) < total,
            "schema":      schema,
            "documents":   documents,
        })

    except frappe.PermissionError:
        return gen_response(403, f"Not permitted for {doctype}")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_document_detail(doctype, name):
    """Detail screen — single document shaped by detail_view_config."""
    try:
        err = _ensure_doctype_configured(doctype)
        if err:
            return err

        _, detail_config = get_doc_config(doctype)
        sections = detail_config.get("sections", [])

        doc = frappe.get_doc(doctype, name)
        currency = _doc_currency(doc)
        state = doc.workflow_state or ""

        return gen_response(200, "Document detail fetched successfully", {
            "name":              name,
            "doctype":           doctype,
            "workflow_state":    state,
            "badge":             badge_color(state),
            "available_actions": _shape_actions(_available_actions(doc)),
            "sections": [{
                "label": sec.get("label", ""),
                "fields": [_shape_field(cfg, doc.get(cfg.get("fieldname")), currency) for cfg in sec.get("fields", [])],
            } for sec in sections],
        })

    except frappe.DoesNotExistError:
        return gen_response(404, f"{doctype} '{name}' not found")
    except frappe.PermissionError:
        return gen_response(403, f"Not permitted for {doctype}")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_document_actions(doctype, name):
    """Quick action-check for a single document."""
    try:
        doc = frappe.get_doc(doctype, name)
        state = doc.workflow_state or ""
        return gen_response(200, "Document actions fetched successfully", {
            "doctype":           doctype,
            "name":              name,
            "workflow_state":    state,
            "badge":             badge_color(state),
            "available_actions": _shape_actions(_available_actions(doc)),
        })
    except frappe.DoesNotExistError:
        return gen_response(404, f"{doctype} '{name}' not found")
    except frappe.PermissionError:
        return gen_response(403, f"Not permitted for {doctype}")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def apply_document_action(doctype, name, action):
    """Apply a workflow action and return updated state + actions."""
    try:
        doc = frappe.get_doc(doctype, name)
        apply_workflow(doc, action)
        doc.reload()
        state = doc.workflow_state or ""
        return gen_response(200, f"Action '{action}' applied successfully", {
            "doctype":           doctype,
            "name":              name,
            "workflow_state":    state,
            "badge":             badge_color(state),
            "available_actions": _shape_actions(_available_actions(doc)),
        })
    except frappe.DoesNotExistError:
        return gen_response(404, f"{doctype} '{name}' not found")
    except frappe.PermissionError:
        return gen_response(403, f"Not permitted to perform '{action}' on {doctype}")
    except Exception as e:
        return exception_handler(e)
