import frappe
from frappe import _
from employee_self_service.mobile.v2.utils import (
    gen_response,
    exception_handler,
    ess_validate,
)
from frappe.desk.form import assign_to
from frappe.handler import upload_file
from frappe.utils import cint

@frappe.whitelist()
@ess_validate(methods=["POST"])
def assign_document(
    doctype,
    docname,
    users,
    description=None
):
    try:
        if not frappe.db.exists(doctype, docname):
            return gen_response(404, "Document not found")

        assign_to.add(
            dict(
                assign_to=users,
                doctype=doctype,
                name=docname,
                description=description or "Assigned From Mobile App"
            )
        )
        return gen_response(
            200,
            "Assignment completed successfully"
        )
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_assignments(doctype, docname):
    try:
        assignments = assign_to.get({
            "doctype": doctype,
            "name": docname
        })

        if not assignments:
            return gen_response(
                200,
                "Assignments fetched successfully",
                {
                    "total_assignments": 0,
                    "assignments": []
                }
            )

        users = [d.owner for d in assignments if d.owner]

        user_details = frappe.get_all(
            "User",
            filters={"name": ["in", users]},
            fields=["name", "full_name", "user_image"]
        )

        user_map = {
            user.name: user
            for user in user_details
        }

        for row in assignments:
            user = user_map.get(row.owner)

            row["full_name"] = user.full_name if user else None
            row["user_image"] = user.user_image if user else None

        return gen_response(
            200,
            "Assignments fetched successfully",
            {
                "total_assignments": len(assignments),
                "assignments": assignments
            }
        )

    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def remove_assignment(
    doctype,
    docname,
    user
):
    try:
        assign_to.remove(
            doctype=doctype,
            name=docname,
            assign_to=user
        )
        return gen_response(
            200,
            "Assignment removed successfully"
        )
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def clear_assignments(
    doctype,
    docname
):
    try:
        assign_to.clear(
            doctype,
            docname
        )
        return gen_response(
            200,
            "All assignments cleared successfully"
        )
    except Exception as e:
        return exception_handler(e)
    

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

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_option_list(doctype,field_name):
    try:
        meta = frappe.get_meta(doctype)
        status_field_meta = meta.get_field(field_name)
        status_options = []

        if status_field_meta and status_field_meta.options:
            status_options = [
                opt.strip()
                for opt in status_field_meta.options.split("\n")
                if opt.strip()
            ]

        return gen_response(
            200,
            "Options fetched successfully",
            status_options,
        )

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_sort_option_list(doctype):
    try:
        meta = frappe.get_meta(doctype)

        options = [
            {"fieldname": "modified", "label": "Last Updated On"},
            {"fieldname": "name",     "label": "ID"},
            {"fieldname": "creation", "label": "Created On"},
        ]

        layout_fieldtypes = {
            "Section Break", "Column Break", "Tab Break",
            "HTML", "Table", "Table MultiSelect",
            "Button", "Image", "Fold", "Heading",
        }

        for df in meta.fields:
            if df.in_list_view and df.fieldtype not in layout_fieldtypes:
                options.append({"fieldname": df.fieldname, "label": df.label})

        return gen_response(200, "Sort options fetched successfully", options)

    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_link_option_list(
    doctype,
    fields=None,
    filters=None,
    start=0,
    page_length=20,
):
    try:
        if not frappe.db.exists("DocType", doctype):
            return gen_response(404, f"DocType '{doctype}' not found")

        link_options = frappe.get_all(
            doctype,
            fields=fields or ["name"],
            filters=filters or [],
            start=cint(start),
            page_length=cint(page_length),
            order_by=f"`tab{doctype}`.modified desc",
        )

        return gen_response(
            200,
            "Link options fetched successfully",
            link_options,
        )

    except frappe.PermissionError:
        return gen_response(
            403,
            "Not permitted to access this DocType."
        )
    except Exception as e:
        return exception_handler(e)

