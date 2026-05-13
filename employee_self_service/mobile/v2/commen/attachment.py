from employee_self_service.mobile.v2.utils import *
import frappe
from frappe.handler import upload_file

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
            file_doc.save()

            return gen_response(200, "File uploaded successfully.", {
                "name": file_doc.name,
                "file_url": file_doc.file_url,
                "file_name": file_doc.file_name,
                "is_private": file_doc.is_private,
            })
        else:
            return gen_response(500, "Please upload a file for attachment.")
        
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to upload this file.")
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