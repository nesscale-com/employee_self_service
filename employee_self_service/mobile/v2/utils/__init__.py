import frappe
import wrapt
from bs4 import BeautifulSoup
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import add_days,add_months, get_first_day, today

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
        if frappe.local.request.method not in methods:
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


# Duration Types Supported in `get_date_range`:
#     - "Current Month"
#     - "Last Month"
#     - "Last 3 Month"
#     - "Last 6 Month"
#     - "Current Financial Year"
#     - "Last Financial Year"
@frappe.whitelist()
def get_date_range(duration_type):
    if duration_type == "Current Month":
        return {"from_date": get_first_day(today()), "to_date": today()}
    if duration_type == "Last Month":
        last_month_end_date = add_days(get_first_day(today()), -1)
        return {
            "from_date": get_first_day(last_month_end_date),
            "to_date": last_month_end_date,
        }
    if duration_type == "Last 3 Month":
        last_month_end_date = add_days(get_first_day(today()), -1)
        last_month_start_month_end_date = add_months(last_month_end_date, -2)
        return {
            "from_date": get_first_day(last_month_start_month_end_date),
            "to_date": last_month_end_date,
        }
    if duration_type == "Last 6 Month":
        last_month_end_date = add_days(get_first_day(today()), -1)
        last_month_start_month_end_date = add_months(last_month_end_date, -5)
        return {
            "from_date": get_first_day(last_month_start_month_end_date),
            "to_date": last_month_end_date,
        }
    if duration_type == "Current Financial Year":
        fiscal_year = get_fiscal_year(today(), as_dict=1)
        if not fiscal_year:
            frappe.throw(_("No Any Financial Year Active"))
        return {
            "from_date": fiscal_year.get("year_start_date"),
            "to_date": fiscal_year.get("year_end_date"),
        }
    if duration_type == "Last Financial Year":
        current_fiscal_year = get_fiscal_year(today(), as_dict=1)
        if not current_fiscal_year:
            frappe.throw(_("No Any Financial Year Active"))
        last_fiscal_year = get_fiscal_year(
            add_days(current_fiscal_year.get("year_start_date"), -1), as_dict=1
        )
        if not last_fiscal_year:
            frappe.throw(_("No Any Data In Last Financial Year"))
        return {
            "from_date": last_fiscal_year.get("year_start_date"),
            "to_date": last_fiscal_year.get("year_end_date"),
        }
    
def get_sales_person_by_customer(party):
    sales_persons = frappe.get_all(
        "Sales Team",
        filters={"parenttype": "Customer", "parent": party},
        fields=["sales_person", "allocated_percentage", "commission_rate"],
    )
    return sales_persons

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
        if doc_data:
            doc_data["workflow_state"] = doc.get("status")
        return []
    try:
        transitions = get_transitions(doc)
    except Exception:
        return []
    actions = []
    for row in transitions:
        actions.append(row.get("action"))
    return actions
