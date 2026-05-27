# Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import cint


# Field types that cannot be rendered as a simple key-value row in the mobile app.
_EXCLUDE_FIELD_TYPES = {
    # Structural / layout
    "Section Break", "Column Break", "Tab Break", "Fold",
    # UI-only
    "HTML", "HTML Editor", "Markdown Editor", "Heading", "Button",
    # Child tables
    "Table", "Table MultiSelect", "Table Break",
    # Long-form / markup content
    "Long Text", "Text Editor", "Code",
    # Binary / file
    "Password", "Attach", "Attach Image", "Signature",
    # Special / non-text
    "Geolocation", "Color", "Rating", "Duration", "Barcode", "JSON",
}


def _sanitize_config(raw, kind):
    """Strip disallowed field types from a saved list/detail config JSON string."""
    if not raw:
        return raw
    try:
        data = json.loads(raw)
    except Exception:
        return raw

    def keep(f):
        return f.get("fieldtype", "Data") not in _EXCLUDE_FIELD_TYPES

    if kind == "list":
        data["fields"] = [f for f in data.get("fields", []) if keep(f)]
    else:
        for sec in data.get("sections", []):
            sec["fields"] = [f for f in sec.get("fields", []) if keep(f)]

    return json.dumps(data)


class ESSWorkflowSettings(Document):
    def validate(self):
        for row in self.ess_workflow_documents:
            row.list_view_config = _sanitize_config(row.list_view_config, "list")
            row.detail_view_config = _sanitize_config(row.detail_view_config, "detail")


# ── Mobile / Flutter configuration ────────────────────────────────────────────
# All lookup tables consumed by the v2 workflow API live here so the API layer
# stays thin and admins can tweak presentation without touching API code.

FLUTTER_TYPE_MAP = {
    "Data": "text", "Small Text": "text", "Text": "text",
    "Long Text": "text", "Text Editor": "text", "Read Only": "text",
    "Code": "text", "Password": "text", "Select": "text",
    "Date": "date", "Datetime": "datetime", "Time": "time",
    "Currency": "currency", "Float": "decimal", "Int": "integer",
    "Percent": "percent", "Check": "boolean",
    "Link": "link", "Dynamic Link": "link",
    "Color": "color", "Rating": "rating", "Duration": "duration",
}

BADGE_COLORS = {
    "draft":              {"bg_color": "#F3F4F6", "text_color": "#6B7280"},
    "open":               {"bg_color": "#EDE9FE", "text_color": "#5B21B6"},
    "pending":            {"bg_color": "#FEF3C7", "text_color": "#92400E"},
    "pending approval":   {"bg_color": "#FEF3C7", "text_color": "#92400E"},
    "pending review":     {"bg_color": "#FEF3C7", "text_color": "#92400E"},
    "approved":           {"bg_color": "#D1FAE5", "text_color": "#065F46"},
    "submitted":          {"bg_color": "#D1FAE5", "text_color": "#065F46"},
    "completed":          {"bg_color": "#DBEAFE", "text_color": "#1E40AF"},
    "closed":             {"bg_color": "#DBEAFE", "text_color": "#1E40AF"},
    "rejected":           {"bg_color": "#FEE2E2", "text_color": "#991B1B"},
    "cancelled":          {"bg_color": "#FEE2E2", "text_color": "#991B1B"},
    "on hold":            {"bg_color": "#F3F4F6", "text_color": "#6B7280"},
}
DEFAULT_BADGE = {"bg_color": "#F3F4F6", "text_color": "#6B7280"}

ACTION_STYLES = {
    "approve":             {"style": "success",   "bg_color": "#22C55E", "text_color": "#FFFFFF"},
    "approved":            {"style": "success",   "bg_color": "#22C55E", "text_color": "#FFFFFF"},
    "reject":              {"style": "danger",    "bg_color": "#EF4444", "text_color": "#FFFFFF"},
    "rejected":            {"style": "danger",    "bg_color": "#EF4444", "text_color": "#FFFFFF"},
    "cancel":              {"style": "danger",    "bg_color": "#EF4444", "text_color": "#FFFFFF"},
    "submit for approval": {"style": "primary",   "bg_color": "#3B82F6", "text_color": "#FFFFFF"},
    "resubmit":            {"style": "warning",   "bg_color": "#F59E0B", "text_color": "#FFFFFF"},
    "revise":              {"style": "warning",   "bg_color": "#F59E0B", "text_color": "#FFFFFF"},
}
DEFAULT_ACTION_STYLE = {"style": "secondary", "bg_color": "#6B7280", "text_color": "#FFFFFF"}

_STANDARD_FIELDS = [
    {"fieldname": "name",           "label": "Document No",   "fieldtype": "Data",     "is_badge": 0, "slot": "id"},
    {"fieldname": "workflow_state", "label": "Status",        "fieldtype": "Data",     "is_badge": 1, "slot": "status"},
    {"fieldname": "modified",       "label": "Last Modified", "fieldtype": "Datetime", "is_badge": 0, "slot": "footer"},
]


def flutter_type(fieldtype, is_badge=False):
    if is_badge:
        return "badge"
    return FLUTTER_TYPE_MAP.get(fieldtype, "text")


def badge_color(state):
    return BADGE_COLORS.get((state or "").lower(), DEFAULT_BADGE)


def action_descriptor(action_name):
    style = ACTION_STYLES.get(action_name.lower(), DEFAULT_ACTION_STYLE)
    return {"action": action_name, "label": action_name, **style}


def _default_list_config():
    return {"fields": list(_STANDARD_FIELDS)}


def _default_detail_config():
    return {"sections": [{"label": "Overview", "fields": list(_STANDARD_FIELDS)}]}


def _parse_config(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def get_settings():
    return frappe.get_cached_doc("ESS Workflow Settings")


def is_enabled():
    return bool(get_settings().enable_workflow_in_ess)


def configured_doctypes():
    return [r.document for r in get_settings().ess_workflow_documents if r.document]


def get_doc_config(doctype):
    """Return (list_config, detail_config) for a doctype, with sensible defaults."""
    for row in get_settings().ess_workflow_documents:
        if row.document == doctype:
            return (
                _parse_config(row.list_view_config) or _default_list_config(),
                _parse_config(row.detail_view_config) or _default_detail_config(),
            )
    return _default_list_config(), _default_detail_config()


@frappe.whitelist()
def get_workflow_doctypes(doctype, txt, searchfield, start, page_len, filters):
    """Query handler for the Document link — returns only DocTypes with an active Workflow."""
    active_doctypes = frappe.get_all(
        "Workflow",
        filters={"is_active": 1},
        pluck="document_type",
    )
    result = [
        [dt]
        for dt in sorted(set(active_doctypes))
        if not txt or txt.lower() in dt.lower()
    ]
    return result[int(start) : int(start) + int(page_len)]


@frappe.whitelist()
def get_doctype_fields(doctype):
    """
    Returns all displayable fields for the given doctype.
    Includes `in_list_view` and `reqd` flags so the Configure dialog
    can use them for the auto-fill buttons.
    """
    meta = frappe.get_meta(doctype)
    fields = []

    # Always lead with the standard fields the mobile side always needs
    standard = [
        {"fieldname": "name",           "label": "Document No",  "fieldtype": "Data",     "in_list_view": 0, "reqd": 0},
        {"fieldname": "workflow_state", "label": "Status",        "fieldtype": "Data",     "in_list_view": 0, "reqd": 0},
        {"fieldname": "modified",       "label": "Last Modified", "fieldtype": "Datetime", "in_list_view": 0, "reqd": 0},
    ]
    seen = {f["fieldname"] for f in standard}
    fields.extend(standard)

    for f in meta.fields:
        if f.fieldtype in _EXCLUDE_FIELD_TYPES:
            continue
        if not f.fieldname or f.fieldname in seen or f.hidden:
            continue
        fields.append({
            "fieldname":   f.fieldname,
            "label":       f.label or f.fieldname,
            "fieldtype":   f.fieldtype,
            "in_list_view": cint(f.in_list_view),
            "reqd":        cint(f.reqd),
        })
        seen.add(f.fieldname)

    return fields


@frappe.whitelist()
def fetch_all_workflow_documents():
    """
    Returns every active-workflow doctype with auto-generated default configs:
      - list_view_config  built from fields marked `in_list_view`
      - detail_view_config built from fields marked `reqd`
    Used by the 'Fetch Workflow Documents' button on the ESS Workflow Settings form.
    """
    active_workflows = frappe.get_all(
        "Workflow",
        filters={"is_active": 1},
        fields=["document_type"],
    )

    result = []
    for wf in active_workflows:
        doctype = wf["document_type"]
        try:
            meta = frappe.get_meta(doctype)
        except Exception:
            continue

        # ── List view: in_list_view fields, capped at 5 (+ status = 6 total) ──
        list_fields = []
        for f in meta.fields:
            if f.fieldtype in _EXCLUDE_FIELD_TYPES or f.hidden or not f.fieldname:
                continue
            if f.in_list_view:
                list_fields.append({
                    "fieldname": f.fieldname,
                    "label":     f.label or f.fieldname,
                    "fieldtype": f.fieldtype,
                    "is_badge":  0,
                    "slot":      "id" if f.fieldname == "name" else "body",
                })

        # Remove workflow_state from in_list_view set so we can pin it at the end
        list_fields = [f for f in list_fields if f["fieldname"] != "workflow_state"]
        # Cap at 5 to always leave the last slot for workflow_state
        list_fields = list_fields[:5]
        list_fields.append({"fieldname": "workflow_state", "label": "Status", "fieldtype": "Data", "is_badge": 1, "slot": "status"})

        # ── Detail view: mandatory fields grouped under "Overview" ───────────
        detail_fields = []
        for f in meta.fields:
            if f.fieldtype in _EXCLUDE_FIELD_TYPES or f.hidden or not f.fieldname:
                continue
            if f.reqd:
                detail_fields.append({
                    "fieldname": f.fieldname,
                    "label":     f.label or f.fieldname,
                    "fieldtype": f.fieldtype,
                    "is_badge":  0,
                })

        # Always prepend name + workflow_state if not already present
        existing_names = {f["fieldname"] for f in detail_fields}
        prefix = []
        if "name" not in existing_names:
            prefix.append({"fieldname": "name", "label": "Document No", "fieldtype": "Data", "is_badge": 0})
        if "workflow_state" not in existing_names:
            prefix.append({"fieldname": "workflow_state", "label": "Status", "fieldtype": "Data", "is_badge": 1})
        else:
            for f in detail_fields:
                if f["fieldname"] == "workflow_state":
                    f["is_badge"] = 1
        detail_fields = prefix + detail_fields

        result.append({
            "document_type":      doctype,
            "list_view_config":   json.dumps({"fields": list_fields}),
            "detail_view_config": json.dumps({"sections": [{"label": "Overview", "fields": detail_fields}]}),
        })

    return result
