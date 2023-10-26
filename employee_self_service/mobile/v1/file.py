import frappe
from frappe import _
from frappe.handler import upload_file
from employee_self_service.mobile.v1.api_utils import (
    exception_handler,
    ess_validate,
    gen_response,
)


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
            file_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return gen_response(200, "file added successfully.")
        else:
            return gen_response(500, "Please upload a file for attachment.")
    except Exception as e:
        frappe.db.rollback()
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
