from employee_self_service.mobile.v2.commen.utils import *


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_holiday_list(year=None):
    try:
        if not year:
            return gen_response(500, "year is required")
        emp_data = get_employee_by_user(frappe.session.user)

        from erpnext.setup.doctype.employee.employee import (
            get_holiday_list_for_employee,
        )

        holiday_list = get_holiday_list_for_employee(
            emp_data.name, raise_exception=False
        )

        if not holiday_list:
            return gen_response(200, "Holiday list get successfully", [])

        holidays = frappe.get_all(
            "Holiday",
            filters={
                "parent": holiday_list,
                "holiday_date": ("between", [f"{year}-01-01", f"{year}-12-31"]),
            },
            fields=["description", "holiday_date"],
            order_by="holiday_date asc",
        )

        if len(holidays) == 0:
            return gen_response(500, f"no holidays found for year {year}")

        holiday_list = []

        for holiday in holidays:
            holiday_date = frappe.utils.data.getdate(holiday.holiday_date)
            holiday_list.append(
                {
                    "year": holiday_date.strftime("%Y"),
                    "date": holiday_date.strftime("%d %b"),
                    "day": holiday_date.strftime("%A"),
                    "description": holiday.description,
                }
            )
        return gen_response(200, "Holiday list get successfully", holiday_list)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def add_comment(reference_doctype=None, reference_name=None, content=None):
    try:
        comment_by = frappe.db.get_value(
            "User", frappe.session.user, "full_name", as_dict=1
        )
        add_ess_comment(
            reference_doctype=reference_doctype,
            reference_name=reference_name,
            content=content,
            comment_email=frappe.session.user,
            comment_by=comment_by.get("full_name"),
        )
        return gen_response(200, "Comment added successfully")

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


@frappe.whitelist()
@ess_validate(methods=["POST"])
def upload_documents():
    try:
        emp_data = get_employee_by_user(frappe.session.user)

        file_doc = upload_file()

        ess_document = frappe.get_doc(
            {
                "doctype": "ESS Documents",
                "employee_no": emp_data.get("name"),
                "title": frappe.form_dict.title,
            }
        ).insert()

        file_doc.attached_to_doctype = "ESS Documents"
        file_doc.attached_to_name = str(ess_document.name)
        file_doc.attached_to_field = "attachement"
        file_doc.save()

        ess_document.attachement = file_doc.file_url
        ess_document.save()

        return gen_response(200, "Document added successfully")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def document_list():
    try:
        from frappe.utils.file_manager import get_file_path

        emp_data = get_employee_by_user(frappe.session.user)
        documents = frappe.get_all(
            "ESS Documents",
            filters={
                "employee_no": emp_data.get("name"),
            },
            fields=["name", "attachement"],
        )

        if documents:
            for doc in documents:
                file = frappe.get_value(
                    "File",
                    {
                        "file_url": doc.get("attachement"),
                        "attached_to_doctype": "ESS Documents",
                        "attached_to_name": doc.get("name"),
                    },
                    ["name", "file_name", "file_size"],
                    as_dict=1,
                )
                if file:
                    doc["file_name"] = file.get("file_name")
                    doc["file_size"] = get_file_size(
                        (get_file_path(file.get("file_name"))), unit="auto"
                    )
                    doc["file_id"] = file.get("name")

            return gen_response(200, "Documents get successfully", documents)
        else:
            return gen_response(200, "No documents found for employee", [])
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_branch():
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["branch"])
        branch = frappe.db.get_value(
            "Branch",
            {"branch": emp_data.get("branch")},
            ["branch", "latitude", "longitude", "radius"],
            as_dict=1,
        )

        return gen_response(200, "Branch", branch)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_customer_list(start=0, page_length=10, filters=None):
    try:
        customer_list = frappe.get_list(
            "Customer",
            ["name", "customer_name", "mobile_no as phone"],
            start=start,
            filters=filters,
            page_length=page_length,
            order_by="modified desc",
        )
        return gen_response(200, "Customer list get successfully", customer_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read customer")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_list():
    try:
        employee = frappe.get_list("Employee", ["name", "employee_name"])
        return gen_response(200, "Employee list Getting Successfully", employee)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read employee")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_supplier_list(start=0, page_length=10, filters=None):
    try:
        supplier_list = frappe.get_list(
            "Supplier",
            ["name", "supplier_name", "mobile_no as phone"],
            start=start,
            filters=filters,
            page_length=page_length,
            order_by="modified desc",
        )
        return gen_response(200, "Supplier list get successfully", supplier_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read supplier")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["DELETE"])
def delete_documents(file_id=None, attached_to_name=None):
    try:
        from frappe.utils.file_manager import remove_file

        attached_to_doctype = "ESS Documents"
        remove_file(
            fid=file_id,
            attached_to_doctype=attached_to_doctype,
            attached_to_name=attached_to_name,
        )
        frappe.delete_doc(attached_to_doctype, attached_to_name, force=1)
        return gen_response(200, "you have successfully deleted ESS Document")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted delete file")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_user_list():
    try:
        user_list = frappe.get_all(
            "User",
            filters={"user_type": "System User", "enabled": 1},
            fields=["name", "full_name", "user_image"],
        )
        return gen_response(200, "User List getting Successfully", user_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read user")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_backend_ess_version():
    try:
        from employee_self_service import __version__

        return gen_response(
            200, "Backend version get successfully", {"version": __version__}
        )
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_hr_policies():
    try:
        current_user = frappe.session.user
        frappe.set_user("Administrator")
        hr_policies_doc = frappe.get_doc("Company Policy")
        frappe.set_user(current_user)
        return gen_response(200, "HR Policy get successfully", hr_policies_doc)
    except Exception as e:
        return exception_handler(e)
