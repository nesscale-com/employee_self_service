from employee_self_service.mobile.v2.utils import (
    gen_response,
    exception_handler,
    ess_validate,
)
import frappe
from frappe.utils import cint
from frappe.handler import upload_file

@frappe.whitelist()
@ess_validate(methods=["POST"])
def upload_documents():
    try:
        form_dict = frappe.form_dict

        reference_doctype = form_dict.get("reference_doctype")
        reference_docname = form_dict.get("reference_docname")

        if not reference_doctype:
            return gen_response(400, "Please provide a reference document type.")

        if not reference_docname:
            return gen_response(400, "Please provide a reference document name.")

        if "file" not in frappe.request.files:
            return gen_response(400, "Please upload a file for attachment.")

        file_doc = upload_file()

        file_doc.update({
            "attached_to_doctype": reference_doctype,
            "attached_to_name": reference_docname,
            "is_private": cint(form_dict.get("is_private", 1))
        })

        file_doc.save()

        return gen_response(
            200,
            "File uploaded successfully.",
            {
                "name": file_doc.name,
                "file_url": file_doc.file_url,
                "file_name": file_doc.file_name,
                "is_private": file_doc.is_private,
            }
        )

    except frappe.PermissionError:
        return gen_response(403, "Not permitted to upload this file.")
    except Exception as e:
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