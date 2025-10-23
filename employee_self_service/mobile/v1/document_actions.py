import frappe

from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def delete_document(refrence_doctype, reference_name):
    try:
        frappe.delete_doc(refrence_doctype, reference_name)
        return gen_response(
            200, f"{refrence_doctype} - {reference_name} deleted successfully."
        )

    except frappe.PermissionError:
        return gen_response(
            403, f"Not permitted to delete {refrence_doctype} - {reference_name}"
        )

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def submit_document(refrence_doctype, reference_name):
    try:
        doc = frappe.get_doc(refrence_doctype, reference_name)
        doc.submit()
        return gen_response(
            200, f"{refrence_doctype} - {reference_name} submitted successfully."
        )
    except frappe.PermissionError:
        frappe.db.rollback()
        return gen_response(
            403, f"Not permitted to submit {refrence_doctype} - {reference_name}"
        )
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def cancel_document(refrence_doctype, reference_name):
    try:
        doc = frappe.get_doc(refrence_doctype, reference_name)
        doc.cancel()
        return gen_response(
            200, f"{refrence_doctype} - {reference_name} cancelled successfully."
        )

    except frappe.PermissionError:
        return gen_response(
            403, f"Not permitted to cancel {refrence_doctype} - {reference_name}"
        )

    except Exception as e:
        return exception_handler(e)
