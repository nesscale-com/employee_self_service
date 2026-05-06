from employee_self_service.mobile.v2.utils import *
from frappe.desk.form import assign_to
from frappe.handler import upload_file
import frappe.model as frappe_model

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
        assignments = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": doctype,
                "reference_name": docname,
                "status": ["!=", "Cancelled"]
            },
            fields=[
                "name",
                "allocated_to",
                "description",
                "status",
                "date"
            ]
        )

        users = list(set([
            d.allocated_to for d in assignments if d.allocated_to
        ]))
        user_details = frappe.get_all(
            "User",
            filters={
                "name": ["in", users]
            },
            fields=[
                "name",
                "full_name",
                "user_image"
            ]
        )

        user_map = {
            user.name: user for user in user_details
        }

        for row in assignments:
            user = user_map.get(row.allocated_to, {})
            row["full_name"] = user.get("full_name")
            row["user_image"] = user.get("user_image")

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
def get_list_sort_options(doctype):
    try:
        if doctype.startswith("tab"):
            doctype = doctype[3:]

        meta = frappe.get_meta(doctype)

        SORTABLE_FIELDTYPES = {
            "Data", "Link", "Select", "Date", "Datetime",
            "Int", "Float", "Currency", "Check",
        }

        sort_fields = [
            {"fieldname": "name",     "label": "ID"},
            {"fieldname": "modified", "label": "Last Updated On"},
            {"fieldname": "creation", "label": "Created On"},
        ]
        added = {"name", "modified", "creation"}

        for df in meta.fields:
            if (
                df.fieldname
                and df.label
                and df.fieldtype in SORTABLE_FIELDTYPES
                and df.fieldname not in added
            ):
                sort_fields.append({"fieldname": df.fieldname, "label": df.label})
                added.add(df.fieldname)

        return gen_response(
            200,
            "Sort options fetched successfully",
            sort_fields,
        )

    except Exception as e:
        return exception_handler(e)

