import frappe
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import today,nowdate
from employee_self_service.mobile.v2.utils import (
    gen_response,
    exception_handler,
    ess_validate,
    get_employee_by_user,
    validate_employee_data
)
from employee_self_service.mobile.v2.module.leave.utils import (
    get_leave_balance_report
)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_leave_application_list():
    """
    Get Leave Application which is already applied. Get Leave Balance Report
    """
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        validate_employee_data(emp_data)
        leave_application_fields = [
            "name",
            "leave_type",
            "DATE_FORMAT(from_date, '%d-%m-%Y') as from_date",
            "DATE_FORMAT(to_date, '%d-%m-%Y') as to_date",
            "total_leave_days",
            "description",
            "status",
            "DATE_FORMAT(posting_date, '%d-%m-%Y') as posting_date",
            "half_day",
            "DATE_FORMAT(half_day_date, '%d-%m-%Y') as half_day_date",
        ]
        upcoming_leaves = frappe.get_all(
            "Leave Application",
            filters={"from_date": [">", today()], "employee": emp_data.get("name")},
            fields=leave_application_fields,
        )

        taken_leaves = frappe.get_all(
            "Leave Application",
            fields=leave_application_fields,
            filters={"from_date": ["<=", today()], "employee": emp_data.get("name")},
        )
        fiscal_year = get_fiscal_year(nowdate())[0]
        if not fiscal_year:
            return gen_response(500, "Fiscal year not set")
        res = get_leave_balance_report(
            emp_data.get("name"), emp_data.get("company"), fiscal_year
        )
        leave_applications = {
            "upcoming": upcoming_leaves,
            "taken": taken_leaves,
            "balance": res,
        }
        return gen_response(200, "Leave data getting successfully", leave_applications)
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_leave_type(from_date=None, to_date=None):
    try:
        from hrms.hr.doctype.leave_application.leave_application import (
            get_leave_balance_on,
        )

        if not from_date:
            from_date = today()
        emp_data = get_employee_by_user(frappe.session.user)
        leave_types = frappe.get_all(
            "Leave Type", filters={}, fields=["name", "'0' as balance"]
        )
        for leave_type in leave_types:
            leave_type["balance"] = get_leave_balance_on(
                emp_data.get("name"),
                leave_type.get("name"),
                from_date,
                consider_all_leaves_in_the_allocation_period=True,
            )
        return gen_response(200, "Leave type get successfully", leave_types)
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_leave_application(*args, **kwargs):
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists!")
        validate_employee_data(emp_data)

        leave_id = kwargs.get("name")
        if not leave_id:
            return gen_response(500, "Leave ID is required!")

        if not frappe.db.exists("Leave Application", kwargs.get("name")):
            return gen_response(500, "Leave application does not exists!")

        leave_application_doc = frappe.get_doc("Leave Application", leave_id)
        leave_application_doc.update(kwargs)
        leave_application_doc.save()
        gen_response(200, "Leave application successfully updated!")
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["POST"])
def make_leave_application(*args, **kwargs):
    try:
        from hrms.hr.doctype.leave_application.leave_application import (
            get_leave_approver,
        )

        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists!")
        validate_employee_data(emp_data)

        leave_application_doc = frappe.get_doc(
            doctype="Leave Application",
            employee=emp_data.get("name"),
            company=emp_data.company,
            leave_approver=get_leave_approver(emp_data.name),
        )
        leave_application_doc.update(kwargs)
        leave_application_doc.insert()
        gen_response(200, "Leave application successfully added!", leave_application_doc.name)
    except Exception as e:
        return exception_handler(e)
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_leave_application(name):
    """
    Get Leave Application which is already applied. Get Leave Balance Report
    """
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        validate_employee_data(emp_data)

        if not frappe.db.exists(
            "Leave Application", {"name": name, "employee": emp_data.get("name")}
        ):
            return gen_response(500, "Leave application does not exists!")

        leave_application_fields = [
            "name",
            "leave_type",
            "total_leave_days",
            "description",
            "status",
            "half_day",
            "from_date",
            "to_date",
            "posting_date",
            "half_day_date"
        ]

        leave_application = frappe.db.get_value(
            "Leave Application", name, leave_application_fields, as_dict=True
        )

        file_data = frappe.db.get_value(
            "File",
            {
                "attached_to_doctype": "Leave Application",
                "attached_to_name": name,
                "attached_to_field": "medical_supporting_document",
            },
            ["file_name","name","file_url"],
            as_dict=True,
        )

        leave_application["medical_supporting_document"] = file_data

        return gen_response(200, "Leave data getting successfully", leave_application)
    except Exception as e:
        return exception_handler(e)

