import frappe
from frappe import _
from employee_self_service.mobile.v2.utils import (
    gen_response,
    exception_handler,
    ess_validate,
    remove_default_fields,
)
from frappe.utils import cint


def _parse_data(data):
    """Accept the request payload either as a dict or a JSON string."""
    if data is None:
        return None
    if isinstance(data, str):
        try:
            data = frappe.parse_json(data)
        except Exception:
            return None
    return data if isinstance(data, dict) else None


def _parse_json(value, default):
    """Parse a value that may arrive as a JSON string (filters/fields)."""
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return frappe.parse_json(value)
        except Exception:
            return default
    return value


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_document(doctype, data=None):
    try:
        if not frappe.db.exists("DocType", doctype):
            return gen_response(404, f"DocType '{doctype}' not found")

        doc_data = _parse_data(data)
        if not doc_data:
            return gen_response(400, "Please provide valid document data.")

        # Never let the payload override the target doctype.
        doc_data["doctype"] = doctype

        doc = frappe.get_doc(doc_data)
        doc.insert()

        return gen_response(
            200,
            "Document created successfully",
            remove_default_fields(doc.as_dict()),
        )

    except frappe.PermissionError:
        return gen_response(403, f"Not permitted to create {doctype}.")
    except frappe.DuplicateEntryError:
        return gen_response(409, "Document with this name already exists.")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_document(doctype, name):
    try:
        if not frappe.db.exists(doctype, name):
            return gen_response(404, f"{doctype} '{name}' not found")

        doc = frappe.get_doc(doctype, name)
        doc.check_permission("read")

        return gen_response(
            200,
            "Document fetched successfully",
            remove_default_fields(doc.as_dict()),
        )

    except frappe.PermissionError:
        return gen_response(403, f"Not permitted to read {doctype}.")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_document(doctype, name, data=None):
    try:
        if not frappe.db.exists(doctype, name):
            return gen_response(404, f"{doctype} '{name}' not found")

        doc_data = _parse_data(data)
        if not doc_data:
            return gen_response(400, "Please provide valid document data.")

        # Identity fields must not be mutated through the update payload.
        doc_data.pop("doctype", None)
        doc_data.pop("name", None)

        doc = frappe.get_doc(doctype, name)
        doc.update(doc_data)
        doc.save()

        return gen_response(
            200,
            "Document updated successfully",
            remove_default_fields(doc.as_dict()),
        )

    except frappe.PermissionError:
        return gen_response(403, f"Not permitted to update {doctype}.")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def delete_document(doctype, name):
    try:
        if not frappe.db.exists(doctype, name):
            return gen_response(404, f"{doctype} '{name}' not found")
        frappe.delete_doc(doctype, name)
        return gen_response(200, "Document deleted successfully")

    except frappe.PermissionError:
        return gen_response(403, f"Not permitted to delete {doctype}.")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_document_list(
    doctype,
    fields=None,
    filters=None,
    order_by=None,
    start=0,
    page_length=20,
):
    try:
        if not frappe.db.exists("DocType", doctype):
            return gen_response(404, f"DocType '{doctype}' not found")

        fields = _parse_json(fields, ["name"])
        filters = _parse_json(filters, {})
        start = cint(start)
        page_length = cint(page_length)
        order_by = order_by or "modified desc"

        records = frappe.get_list(
            doctype,
            fields=fields,
            filters=filters,
            order_by=order_by,
            limit_start=start,
            limit_page_length=page_length,
        )

        return gen_response(
            200,
            "Document list fetched successfully",
            records,
        )

    except frappe.PermissionError:
        return gen_response(403, f"Not permitted to access {doctype}.")
    except Exception as e:
        return exception_handler(e)
