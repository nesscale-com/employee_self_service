import frappe
import json
from frappe import _
from frappe.utils import today
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    remove_default_fields,
    get_global_defaults,
)
from employee_self_service.mobile.v1.manager.manager_utils import get_action

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats():
    try:
        stats = {
            "total_employees": 0,
            "clock_in": 0,
            "clock_out": 0,
            "on_leave": 0,
            "not_clock_in": 0,
            "approval": 13,
            "tasks": 40
        }

        # Step-1: Get all employees that current user has permission to access
        employee_list = frappe.get_list("Employee", 
                                      filters={"status": "Active"}, 
                                      pluck="name")
        
        if not employee_list:
            frappe.throw(_("No active employees found"))
        
        stats["total_employees"] = len(employee_list)
        
        # Step-2: Get all check-ins for today for these employees
        checkins_today = frappe.get_all("Employee Checkin",
                            filters={
                                "time": ["between", [f"{today()} 00:00:00", f"{today()} 23:59:59"]],
                                "employee": ["in", employee_list]
                            },
                            fields=["employee", "log_type"])
        
        employee_check_in_today = [emp["employee"] for emp in checkins_today]

        for checkin in checkins_today:
            if checkin["log_type"] == "IN":
                stats["clock_in"] += 1
            elif checkin["log_type"] == "OUT":
                stats["clock_out"] += 1
        
        # Step-3: Get leave applications for these employees
        employees_on_leave = frappe.get_all("Leave Application",
                                filters={
                                    "status": "Approved",
                                    "docstatus": 1,
                                    "from_date": ["<=", today()],
                                    "to_date": [">=", today()],
                                    "employee": ["in", employee_list]
                                },
                                pluck="employee")
        
        stats["on_leave"] = len(employees_on_leave)

        # Step-4: Get not_clock_in employees
        for emp in employee_list:
            if emp not in employee_check_in_today and emp not in employees_on_leave:
                stats["not_clock_in"] += 1
        
        return gen_response(200, "Stats retrieved successfully", stats)
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats_list(type):
    try:
        data = [
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
            {
                "image": "/files/logo.svg" ,
                "name": "Nilesh Makwana"
            },
        ]
        return gen_response(200, "Stats get successfully", data)
    except Exception as e:
        return exception_handler(e)