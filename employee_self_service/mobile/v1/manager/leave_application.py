import frappe
import json
from frappe import _
from frappe.utils import pretty_date, getdate
from frappe.utils.data import now_datetime
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    remove_default_fields,
)
from employee_self_service.mobile.v1.manager.manager_utils import get_action

@frappe.whitelist()
@ess_validate(methods=["GET"])
def my_team_leave_application():
    try:
        emp_data = get_employee_by_user(frappe.session.user,fields=["name","image","department"])
        leave_application_fields = [
            "name",
            "leave_type",
            "DATE_FORMAT(from_date, '%d-%m-%Y') as from_date",
            "DATE_FORMAT(to_date, '%d-%m-%Y') as to_date",
            "total_leave_days",
            "description",
            "status",
            "DATE_FORMAT(posting_date, '%d-%m-%Y') as posting_date",
            "employee_name",
            "employee"
        ]
        filters = [
            ["employee","!=",emp_data.get("name")]
        ]
        team_leaves = frappe.get_list(
            "Leave Application",
            filters=filters,
            fields=leave_application_fields,
            order_by="posting_date desc"
        )
        for row in team_leaves:
            row["department"] = emp_data.get("department")
            row["user_image"] = emp_data.get("image")
            row["workflow"] = False
            row["action"] = get_action("Leave Application",row.get("name"),row.get("status"),row)
        return gen_response(200,"Team leave application get successfully",team_leaves)
    except Exception as e:
        return exception_handler(e)