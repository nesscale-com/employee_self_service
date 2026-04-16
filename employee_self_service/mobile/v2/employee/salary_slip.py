import frappe
from frappe import _
from employee_self_service.mobile.v1.auth.utils import *
from employee_self_service.mobile.v1.employee.utils import *

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_salary_sllip():
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        if not len(emp_data) >= 1:
            return gen_response(500, "Employee does not exists")
        validate_employee_data(emp_data)
        salary_slip_list = frappe.get_all(
            "Salary Slip",
            filters={"employee": emp_data.get("name")},
            fields=["posting_date", "name"],
        )
        ss_data = []
        for ss in salary_slip_list:
            ss_details = {}
            month_year = get_month_year_details(ss)
            ss_details["month_year"] = month_year
            ss_details["salary_slip_id"] = ss.name
            ss_details["details"] = get_salary_slip_details(ss.name)
            ss_data.append(ss_details)
        return gen_response(200, "Salary slip details get successfully", ss_data)
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET", "POST"])
def download_salary_slip(ss_id):
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        res = frappe.get_doc("Salary Slip", ss_id)
        if not emp_data.get("name") == res.get("employee"):
            return gen_response(
                500, "Does not have persmission to read this salary slip"
            )
        default_print_format = frappe.db.get_single_value(
            "Employee Self Service Settings",
            "default_print_format",
        )
        if not default_print_format:
            default_print_format = (
                frappe.db.get_value(
                    "Property Setter",
                    dict(property="default_print_format", doc_type=res.doctype),
                    "value",
                )
                or "Standard"
            )
        language = frappe.get_system_settings("language")
        # return  frappe.utils.get_url()
        f"{frappe.utils.get_url()}/{res.doctype}/{res.name}?format={default_print_format or 'Standard'}&_lang={language}&key={res.get_signature()}"
        # return url
        download_pdf(res.doctype, res.name, default_print_format, res)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def download_pdf(doctype, name, format=None, doc=None, no_letterhead=0):
    from frappe.utils.pdf import get_pdf

    html = frappe.get_print(doctype, name, format, doc=doc, no_letterhead=no_letterhead)
    frappe.local.response.filename = "{name}.pdf".format(
        name=name.replace(" ", "-").replace("/", "-")
    )
    frappe.local.response.filecontent = get_pdf(html)
    frappe.local.response.type = "download"
