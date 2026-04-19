import frappe
from frappe.handler import upload_file

from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
    get_employee_by_user,
)

# Mapping of document type keys to their doctype name and image field
DOCUMENT_IMAGE_MAP = {
    "visit": {
        "doctype": "Visit",
        "field": "visit_proof",
        "employee_field": "employee",
    },
}


@frappe.whitelist()
@ess_validate(methods=["POST"])
def upload_documents():
    try:
        if not frappe.form_dict.reference_doctype:
            return gen_response(500, "Please provide a reference document type.")
        if not frappe.form_dict.reference_docname:
            return gen_response(500, "Please provide a reference document name.")
        if "file" in frappe.request.files:
            file_doc = upload_file()
            file_doc.attached_to_doctype = frappe.form_dict.reference_doctype
            file_doc.attached_to_name = frappe.form_dict.reference_docname
            is_private = frappe.form_dict.get("is_private", "1")
            file_doc.is_private = int(is_private)
            file_doc.save(ignore_permissions=True)
            return gen_response(200, "File uploaded successfully.", {
                "name": file_doc.name,
                "file_url": file_doc.file_url,
                "file_name": file_doc.file_name,
                "is_private": file_doc.is_private,
            })
        else:
            return gen_response(500, "Please upload a file for attachment.")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def delete_file(file_name):
    try:
        if not file_name:
            return gen_response(500, "Please provide the file name.")
        if not frappe.db.exists("File", file_name):
            return gen_response(404, "File not found.")
        frappe.delete_doc("File", file_name)
        return gen_response(200, "File deleted successfully.")
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to delete this file.")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_attachments(reference_doctype, reference_name):
    try:
        if not reference_doctype:
            return gen_response(500, "Please provide a reference document type.")
        if not reference_name:
            return gen_response(500, "Please provide a reference document name.")
        files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": reference_doctype,
                "attached_to_name": reference_name,
            },
            fields=["name", "file_name", "file_url", "is_private", "file_size"],
        )
        return gen_response(200, "Attachments fetched successfully.", files)
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to view attachments.")
    except Exception as e:
        return exception_handler(e)


def get_attchment(reference_doctype, reference_name):
    return frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": reference_doctype,
            "attached_to_name": reference_name,
        },
        fields=["*"],
    )


@frappe.whitelist()
@ess_validate(methods=["POST"])
def attach_document_image(document_type, document_name):
    """
    Generic API to attach an image to a supported document.
    Args:
        document_type: Key from DOCUMENT_IMAGE_MAP (e.g. "checkin", "visit")
        document_name: The document ID (e.g. "HR-CHK-00001", "VISIT00001")
    """
    try:
        # Validate document_type
        doc_config = DOCUMENT_IMAGE_MAP.get(document_type)
        if not doc_config:
            return gen_response(
                400,
                f"Unsupported document type '{document_type}'. Supported types: {', '.join(DOCUMENT_IMAGE_MAP.keys())}",
            )

        doctype = doc_config["doctype"]
        image_field = doc_config["field"]
        employee_field = doc_config["employee_field"]

        # Validate document exists
        if not frappe.db.exists(doctype, document_name):
            return gen_response(404, f"{doctype} '{document_name}' not found")

        # Get the document
        doc = frappe.get_doc(doctype, document_name)

        # Verify the document belongs to the current user's employee
        emp_data = get_employee_by_user(frappe.session.user)
        if doc.get(employee_field) != emp_data.get("name"):
            return gen_response(403, "You don't have permission to attach image to this document")

        # Check if file is in request
        if "file" not in frappe.request.files:
            return gen_response(400, "No file provided")

        # Delete old image if exists
        old_file_url = doc.get(image_field)
        if old_file_url:
            old_file_doc = frappe.db.get_value("File", {"file_url": old_file_url}, "name")
            if old_file_doc:
                frappe.delete_doc("File", old_file_doc, ignore_permissions=True)

        # Upload new file
        file = upload_file()
        file.attached_to_doctype = doctype
        file.attached_to_name = doc.name
        file.attached_to_field = image_field
        file.save(ignore_permissions=True)

        # Update document with image URL
        doc.set(image_field, file.get("file_url"))
        doc.save(ignore_permissions=True)

        return gen_response(
            200,
            "Image attached successfully",
            {
                "document_type": document_type,
                "document_name": doc.name,
                "file_url": file.get("file_url"),
                "file_name": file.get("file_name"),
            },
        )
    except Exception as e:
        return exception_handler(e)
