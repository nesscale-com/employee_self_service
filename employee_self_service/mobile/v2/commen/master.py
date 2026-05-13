from employee_self_service.mobile.v2.utils import *
import frappe,erpnext
from frappe.utils import cint,pretty_date

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
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_ess_custom_fields(doctype_name):
    try:
        if not frappe.db.exists("ESS Custom Field", doctype_name):
            return gen_response(200, "No custom fields found for this form", [])
        custom_field_doc = frappe.get_doc("ESS Custom Field", doctype_name)
        return gen_response(
            200, "Custom fields retrieved successfully", custom_field_doc
        )
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_company_list():
    try:
        company_list = frappe.get_list("Company", pluck="name")
        return gen_response(
            200,
            "Company List get successfully",
            company_list,
        )
    except frappe.PermissionError:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_cost_center(company):
    try:
        cost_centers = frappe.get_list(
            "Cost Center", filters={"company": company, "is_group": 0}, fields=["name"]
        )
        return gen_response(200, "Cost Center list get successfully", cost_centers)
    except frappe.PermissionError:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_approver(document_type):
    try:
        from hrms.hr.doctype.department_approver.department_approver import (
            get_approvers,
        )

        emp_data = get_employee_by_user(frappe.session.user)
        leave_approver = get_approvers(
            doctype=document_type,
            txt="",
            searchfield="",
            start=0,
            page_len=20,
            filters={"employee": emp_data.name, "doctype": document_type},
        )
        keys = ["user", "first_name", "last_name"]
        mapped_data = [dict(zip(keys, row)) for row in leave_approver]
        return gen_response(200, "approver receive successfully", mapped_data)
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_default_company_cost_center(company):
    try:
        return gen_response(
            200,
            "default cost center get successfully",
            erpnext.get_default_cost_center(company),
        )
    except frappe.PermissionError:
        return gen_response(500, frappe.flags.error_message)
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_comments(reference_doctype=None, reference_name=None):
    """
    reference_doctype: doctype
    reference_name: docname
    """
    try:
        filters = [
            ["Comment", "reference_doctype", "=", f"{reference_doctype}"],
            ["Comment", "reference_name", "=", f"{reference_name}"],
            ["Comment", "comment_type", "=", "Comment"],
        ]
        comments = frappe.get_all(
            "Comment",
            filters=filters,
            fields=[
                "content as comment",
                "comment_by",
                "creation",
                "comment_email",
            ],
        )

        for comment in comments:
            user_image = frappe.get_value(
                "User", comment.comment_email, "user_image", cache=True
            )
            comment["user_image"] = user_image
            comment["commented"] = pretty_date(comment["creation"])
            comment["creation"] = comment["creation"].strftime("%I:%M %p")

        return gen_response(200, "Comments get successfully", comments)

    except Exception as e:
        return exception_handler(e)