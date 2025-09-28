import frappe
from frappe.desk.search import search_widget, build_for_autosuggest
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
)
from frappe.desk.form.utils import remove_attach


@frappe.whitelist()
@ess_validate(methods=["POST"])
def mobile_search_link(doctype, txt="", start=0, page_length=20, filters=None):
    try:
        results = search_widget(
            doctype=doctype,
            txt=txt,
            start=start,
            page_length=page_length,
            filters=filters,
        )
        return gen_response(
            200,
            "Search results received successfully",
            build_for_autosuggest(results, doctype=doctype),
        )
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_field_options(doctype_name, field_name):
    try:
        if not doctype_name or not field_name:
            return gen_response(
                400, "Both doctype_name and field_name are required", []
            )

        # Check if doctype exists
        if not frappe.db.exists("DocType", doctype_name):
            return gen_response(404, f"DocType '{doctype_name}' not found", [])

        # Get the doctype meta
        doctype_meta = frappe.get_meta(doctype_name)

        # Get the specific field
        field_meta = doctype_meta.get_field(field_name)

        if not field_meta:
            return gen_response(
                404, f"Field '{field_name}' not found in DocType '{doctype_name}'", []
            )

        # Only handle Select fields
        if field_meta.fieldtype != "Select":
            return gen_response(400, f"Field '{field_name}' is not a Select field", [])

        # Parse options for Select fields
        options_list = []
        if field_meta.options:
            for option in field_meta.options.split("\n"):
                if option.strip():
                    options_list.append(option.strip())

        return gen_response(
            200, f"Select field options retrieved successfully", options_list
        )

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def ess_remove_attachment(file_url, doctype, docname):
    try:
        attachments = frappe.get_all(
            "File", filters={"file_url": file_url}, fields=["name"]
        )
        for attachment in attachments:
            remove_attach(attachment.name)

    except Exception as e:
        return exception_handler(e)
