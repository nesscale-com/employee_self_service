import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.utils import cstr
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
import wrapt


def gen_response(status, message, data=[]):
    frappe.response["http_status_code"] = status
    if status == 500:
        frappe.response["message"] = BeautifulSoup(str(message)).get_text()
    else:
        frappe.response["message"] = message
    frappe.response["data"] = data


def exception_handler(e):
    frappe.log_error(title="ESS Mobile App Error", message=frappe.get_traceback())
    if hasattr(e, "http_status_code"):
        return gen_response(e.http_status_code, BeautifulSoup(str(e)).get_text())
    else:
        return gen_response(500, BeautifulSoup(str(e)).get_text())


def generate_key(user):
    user_details = frappe.get_doc("User", user)
    api_secret = api_key = ""
    if not user_details.api_key and not user_details.api_secret:
        api_secret = frappe.generate_hash(length=15)
        # if api key is not set generate api key
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key
        user_details.api_secret = api_secret
        user_details.save(ignore_permissions=True)
    else:
        api_secret = user_details.get_password("api_secret")
        api_key = user_details.get("api_key")
    return {"api_secret": api_secret, "api_key": api_key}


def ess_validate(methods):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        if not frappe.local.request.method in methods:
            return gen_response(500, "Invalid Request Method")
        return wrapped(*args, **kwargs)

    return wrapper


def get_employee_by_user(user, fields=["name"]):
    if isinstance(fields, str):
        fields = [fields]
    emp_data = frappe.get_cached_value(
        "Employee",
        {"user_id": user},
        fields,
        as_dict=1,
    )
    return emp_data


def validate_employee_data(employee_data):
    if not employee_data.get("company"):
        return gen_response(
            500,
            "Company not set in employee doctype. Contact HR manager for set company",
        )


def get_ess_settings():
    return frappe.get_doc(
        "Employee Self Service Settings", "Employee Self Service Settings"
    )


def get_global_defaults():
    return frappe.get_doc("Global Defaults", "Global Defaults")


def remove_default_fields(data):
    # Example usage:
    # remove_default_fields(
    #     json.loads(
    #         frappe.get_doc("Address", "name").as_json()
    #     )
    # )
    for row in [
        "owner",
        "creation",
        "modified",
        "modified_by",
        "docstatus",
        "idx",
        "doctype",
        "links",
    ]:
        if data.get(row):
            del data[row]
    return data


def prepare_json_data(key_list, data):
    return_data = {}
    for key in data:
        if key in key_list:
            return_data[key] = data.get(key)
    return return_data


def get_actions(doc, doc_data=None):
    from frappe.model.workflow import get_transitions

    if not frappe.db.exists(
        "Workflow", dict(document_type=doc.get("doctype"), is_active=1)
    ):
        doc_data["workflow_state"] = doc.get("status")
        return []
    transitions = get_transitions(doc)
    actions = []
    for row in transitions:
        actions.append(row.get("action"))
    return actions


def check_workflow_exists(doctype):
    doc_workflow = frappe.get_all(
        "Workflow",
        filters={"document_type": doctype, "is_active": 1},
        fields=["workflow_state_field"],
    )
    if doc_workflow:
        return doc_workflow[0].workflow_state_field
    else:
        return False


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_workflow_state(reference_doctype, reference_name, action):
    try:
        from frappe.model.workflow import apply_workflow

        doc = frappe.get_doc(reference_doctype, reference_name)
        apply_workflow(doc, action)
        return gen_response(200, "Workflow State Updated Successfully")
    except frappe.PermissionError:
        return gen_response(500, f"Not permitted for update {reference_doctype}")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)


def convert_timezone(timestamp, from_tz, to_tz):
    from pytz import UnknownTimeZoneError, timezone

    from_zone = timezone(from_tz)
    to_zone = timezone(to_tz)

    # If the datetime object is naive (no tzinfo), localize it
    if timestamp.tzinfo is None:
        timestamp = from_zone.localize(timestamp)
    else:
        # If tz-aware but not in expected timezone, normalize it
        timestamp = timestamp.astimezone(from_zone)

    # Convert to target timezone
    return timestamp.astimezone(to_zone)


def get_system_timezone() -> str:
    """Return the system timezone."""
    return (
        frappe.get_system_settings("time_zone") or "Asia/Kolkata"
    )  # Default to India ?!


def get_till_date_holiday_month_wise(emp_data, start_date, end_date):
    holiday_list = get_holiday_list_for_employee(emp_data.name, raise_exception=False)
    if not holiday_list:
        return 0

    return frappe.db.count(
        "Holiday",
        filters={
            "parent": holiday_list,
            "holiday_date": ("between", [start_date, end_date]),
        },
    )


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


def get_attachments(document_type, document):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": document_type, "attached_to_name": document},
        fields=["file_url", "file_name"],
    )


@frappe.whitelist(allow_guest=True)
def ping():
    return "pong"
