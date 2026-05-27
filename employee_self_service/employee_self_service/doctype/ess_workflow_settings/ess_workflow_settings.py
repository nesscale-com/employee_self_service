# Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class ESSWorkflowSettings(Document):
    pass


_EXCLUDE_FIELD_TYPES = {
    "Section Break", "Column Break", "HTML", "Tab Break",
    "Heading", "Button", "Fold", "HTML Editor", "Markdown Editor",
}


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

        # ── List view: in_list_view fields, capped at 5 ─────────────────────
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
                })

        # Remove workflow_state from in_list_view set so we can pin it at the end
        list_fields = [f for f in list_fields if f["fieldname"] != "workflow_state"]
        # Cap at 4 to always leave the last slot for workflow_state
        list_fields = list_fields[:4]
        list_fields.append({"fieldname": "workflow_state", "label": "Status", "fieldtype": "Data", "is_badge": 1})

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
