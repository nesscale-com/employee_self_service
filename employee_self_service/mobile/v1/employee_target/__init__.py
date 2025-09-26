import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)
from frappe.utils import flt


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_list(filters=None):
    try:
        employee = get_employee_by_user(frappe.session.user)
        if not employee:
            return gen_response(500, "Employee not found for this user")

        filters = filters or []
        target_list = frappe.get_all(
            "Employee Target Entry",
            filters=(filters + [["employee", "=", employee.get("name")]]),
            fields=[
                "name",
                "target_template",
                "status",
                "ROUND(progress, 2) as progress",
                "frequency",
                "fiscal_year",
                "month",
                "quarter",
                "start_date",
                "end_date",
                "total_target",
                "total_achieved",
            ],
        )

        return gen_response(200, "Employee Targets get successfully", target_list)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_details(target_id=None):
    try:
        if not target_id:
            return gen_response(400, "Target ID is required")

        target_doc = frappe.get_doc("Employee Target Entry", target_id).as_dict()

        return gen_response(200, "Employee Target Details get successfully", target_doc)
    except frappe.PermissionError:
        return gen_response(403, "Unauthorized to access this target")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_order_details(target_id=None):
    try:
        if not target_id:
            return gen_response(400, "Target ID is required")

        target_log_list = frappe.get_all(
            "SP Target Log",
            filters={"employee_target_entry": target_id},
            fields=["reference_doctype", "reference_docname", "metric"],
        )
        if not target_log_list:
            return gen_response(
                404, "No target order/invoice found for the given Target ID"
            )

        module_details = []
        total_amount = 0
        total_qty = 0
        metric = target_log_list[0].metric if target_log_list else None

        selected_fields = [
            "name",
            "customer",
            "customer_name",
            "transaction_date",
            "total",
            "grand_total",
            "total_commission",
            "status",
        ]

        for log in target_log_list:
            # Fetch only selected fields
            module_doc = frappe.db.get_value(
                log.reference_doctype,
                log.reference_docname,
                selected_fields,
                as_dict=True,
            )
            if not module_doc:
                continue

            module_details.append(module_doc)

            if log.metric == "Value":
                total_amount += flt(
                    module_doc.get("grand_total") or module_doc.get("amount") or 0
                )
            elif log.metric == "Quantity":
                total_qty += flt(
                    module_doc.get("total_qty") or module_doc.get("qty") or 0
                )

        return gen_response(
            200,
            "Employee Target Order Details get successfully",
            {
                "metric": metric,
                "total_orders": len(module_details),
                "total_amount": total_amount,
                "total_qty": total_qty,
                "orders": module_details,
            },
        )

    except frappe.PermissionError:
        return gen_response(403, "Unauthorized to access this target")
    except Exception as e:
        return exception_handler(e)
