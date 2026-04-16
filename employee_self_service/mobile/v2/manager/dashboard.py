import frappe
from frappe.utils import today

from employee_self_service.mobile.v2.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
)


def _employee_sets_today(emp_list):
    if not emp_list:
        return set(), set(), set(), set()

    start = f"{today()} 00:00:00"
    end = f"{today()} 23:59:59"

    in_set = set(
        frappe.get_all(
            "Employee Checkin",
            filters={
                "time": ["between", [start, end]],
                "employee": ["in", emp_list],
                "log_type": "IN",
            },
            pluck="employee",
        )
    )

    out_set = set(
        frappe.get_all(
            "Employee Checkin",
            filters={
                "time": ["between", [start, end]],
                "employee": ["in", emp_list],
                "log_type": "OUT",
            },
            pluck="employee",
        )
    )

    leave_set = set(
        frappe.get_all(
            "Leave Application",
            filters={
                "status": "Approved",
                "docstatus": 1,
                "from_date": ["<=", today()],
                "to_date": [">=", today()],
                "employee": ["in", emp_list],
            },
            pluck="employee",
        )
    )

    not_in_set = set(emp_list) - in_set - leave_set - out_set
    return in_set, out_set, leave_set, not_in_set


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
            "approval": 0,
            "tasks": 0,
        }

        # permitted active employees
        emp_list = (
            frappe.get_list("Employee", filters={"status": "Active"}, pluck="name")
            or []
        )
        stats["total_employees"] = len(emp_list)

        in_set, out_set, leave_set, not_in_set = _employee_sets_today(emp_list)

        stats["clock_in"] = len(in_set)
        stats["clock_out"] = len(out_set)
        stats["on_leave"] = len(leave_set)
        stats["not_clock_in"] = len(not_in_set)

        return gen_response(200, "Stats retrieved successfully", stats)
    except Exception as e:
        return exception_handler(e)


# type must be one of: clock_in, clock_out, on_leave, not_clock_in
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats_list(type):
    try:
        kind = (type or "").strip().lower()
        if kind not in {"clock_in", "clock_out", "on_leave", "not_clock_in"}:
            return gen_response(
                400,
                "Invalid type",
                {"allowed": ["clock_in", "clock_out", "on_leave", "not_clock_in"]},
            )

        emp_list = (
            frappe.get_list("Employee", filters={"status": "Active"}, pluck="name")
            or []
        )
        if not emp_list:
            return gen_response(200, "No employees", [])

        in_set, out_set, leave_set, not_in_set = _employee_sets_today(emp_list)
        bucket = {
            "clock_in": in_set,
            "clock_out": out_set,
            "on_leave": leave_set,
            "not_clock_in": not_in_set,
        }[kind]

        if not bucket:
            return gen_response(200, "No records", [])

        # fetch display info once
        rows = frappe.get_all(
            "Employee",
            filters={"name": ["in", list(bucket)]},
            fields=["name", "employee_name", "image", "gender"],
        )
        data = [
            {
                "employee": r.name,
                "name": r.employee_name or r.name,
                "image": r.image or "",
                "gender": r.gender,
            }
            for r in rows
        ]

        # optional: keep UI stable by name ordering (simple)
        data.sort(key=lambda x: x["name"].lower())

        return gen_response(200, "Stats fetched successfully", data)
    except Exception as e:
        return exception_handler(e)
