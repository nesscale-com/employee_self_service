import frappe
from datetime import datetime
from frappe import _
import json


from erpnext.accounts.utils import getdate
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    prepare_json_data,
    get_employee_by_user,
    exception_handler,
)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_visit(**kwargs):
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        data = kwargs
        if data.get("name"):
            if not frappe.db.exists("Visit", data.get("name")):
                return gen_response(500, "Invalid Visit id.")
            visit_doc = frappe.get_doc("Visit", data.get("name"))
            if not frappe.db.exists("Customer", data.get("customer")):
                visit_doc.set("customer_name", data.get("customer"))
            else:
                visit_doc.customer = data.get("customer")
                visit_doc.customer_name = (
                    frappe.db.get_value(
                        "Customer", data.get("customer"), "customer_name"
                    )
                    or ""
                )

            visit_doc.date = data.get("date")
            visit_doc.time = data.get("time")
            visit_doc.visit_type = data.get("visit_type")
            visit_doc.description = data.get("description")
            visit_doc.location = data.get("location")
            visit_doc.employee = emp_data.get("name")
            visit_doc.save(ignore_permissions=True)
            return gen_response(200, "Visit updated Successfully")
        else:
            visit_doc = frappe.new_doc("Visit")
            if not frappe.db.exists("Customer", data.get("customer")):
                visit_doc.set("customer_name", data.get("customer"))
            else:
                visit_doc.customer = data.get("customer")
            visit_doc.date = data.get("date")
            visit_doc.time = data.get("time")
            visit_doc.visit_type = data.get("visit_type")
            visit_doc.description = data.get("description")
            visit_doc.location = data.get("location")
            visit_doc.employee = emp_data.get("name")
            visit_doc.insert()
            return gen_response(200, "Visit created Successfully")
    except frappe.PermissionError:
        return gen_response(500,"Not permitted create visit")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_visit_list():
    try:
        visit_list = frappe.get_list(
            "Visit",
            fields=[
                "name",
                "customer_name",
                "DATE_FORMAT(date, '%d-%m-%Y') as date",
                "time_format(time, '%h:%i:%s') as time",
                "visit_type",
            ],
        )
        return gen_response(200, "Visit list get successfully", visit_list)
    except frappe.PermissionError:
        return gen_response(500,"Not permitted read visit")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_visit(**kwargs):
    try:
        data = kwargs
        visit_doc = json.loads(frappe.get_doc("Visit", data.get("name")).as_json())
        date = getdate(visit_doc["date"])
        visit_doc["date"] = date.strftime("%d-%m-%Y")
        visit_doc["time"] = datetime.strptime(visit_doc["time"], "%H:%M:%S").strftime(
            "%I:%M:%S"
        )
        visit_data = prepare_json_data(
            [
                "name",
                "customer",
                "customer_name",
                "date",
                "time",
                "visit_type",
                "description",
                "location",
                "employee",
                "user",
            ],
            visit_doc,
        )
        return gen_response(200, "Visit detail get Succesfully", visit_data)
    except frappe.PermissionError:
        return gen_response(500,"Not permitted read visit")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_visit_type():
    try:
        visit_type = frappe.get_all("Visit Type", filters={}, fields=["name"])
        return gen_response(200, "Visit Type Get Successfully", visit_type)
    except Exception as e:
        return exception_handler(e)
