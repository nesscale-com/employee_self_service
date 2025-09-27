import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)
from frappe.utils import flt, fmt_money
from datetime import datetime


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_list(filters=None):
    try:
        employee = get_employee_by_user(frappe.session.user)
        if not employee:
            return gen_response(500, "Employee not found for this user")

        filters = filters or []
        filters.append(["employee", "=", employee.get("name")])

        target_list = frappe.get_all(
            "Employee Target Entry",
            filters=filters,
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
        default_currency = frappe.get_single("Global Defaults").default_currency
        for row in target_list:
            row["total_target"] = fmt_money(
                row.get("total_target") or 0.0, currency=default_currency
            )
            row["total_achieved"] = fmt_money(
                row.get("total_achieved") or 0.0, currency=default_currency
            )
            row["start_date"] = datetime.strftime(row.get("start_date"), "%d-%m-%Y")
            row["end_date"] = datetime.strftime(row.get("end_date"), "%d-%m-%Y")

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
        default_currency = frappe.get_single("Global Defaults").default_currency

        # Format dates safely
        for field in ["start_date", "end_date"]:
            if target_doc.get(field):
                target_doc[field] = datetime.strftime(target_doc[field], "%d-%m-%Y")

        # Format amounts
        for field in ["total_target", "total_achieved"]:
            target_doc[field] = fmt_money(
                target_doc.get(field) or 0.0, currency=default_currency
            )

        # Format child table amounts
        for item_group in target_doc.get("item_group_wise_target", []):
            for field in ["target", "achieved"]:
                item_group[field] = fmt_money(
                    item_group.get(field) or 0.0, currency=default_currency
                )

        return gen_response(200, "Employee Target Details get successfully", target_doc)
    except frappe.PermissionError:
        return gen_response(403, "Unauthorized to access this target")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_order_details_old(target_id=None):
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

        # Get default currency for formatting
        default_currency = frappe.get_single("Global Defaults").default_currency

        for log in target_log_list:
            module_doc = frappe.db.get_value(
                log.reference_doctype,
                log.reference_docname,
                selected_fields,
                as_dict=True,
            )
            if not module_doc:
                continue

            # Format numeric fields as currency
            for field in ["grand_total", "total", "total_commission"]:
                if module_doc.get(field) is not None:
                    module_doc[field] = fmt_money(
                        module_doc[field], currency=default_currency
                    )

            # Format date field
            if module_doc.get("transaction_date"):
                module_doc["transaction_date"] = datetime.strftime(
                    module_doc["transaction_date"], "%d-%m-%Y"
                )

            module_details.append(module_doc)

            if log.metric == "Value":
                total_amount += flt(module_doc.get("grand_total") or 0)
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
                "total_amount": fmt_money(total_amount, currency=default_currency),
                "total_qty": str(total_qty),
                "orders": module_details,
            },
        )

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

        target_logs = frappe.get_all(
            "SP Target Log",
            filters={"employee_target_entry": target_id},
            fields=["reference_doctype", "reference_docname", "metric"],
        )
        if not target_logs:
            return gen_response(
                404, "No target order/invoice found for the given Target ID"
            )

        metric = target_logs[0].metric
        selected_fields = [
            "name",
            "customer_name",
            "transaction_date",
            "total",
            "total_qty",
            "status",
        ]
        default_currency = frappe.get_single("Global Defaults").default_currency

        module_details, total_amount, total_qty = [], 0, 0

        for log in target_logs:
            module_doc = frappe.db.get_value(
                log.reference_doctype,
                {"name": log.reference_docname, "status": ["!=", "Cancelled"]},
                selected_fields,
                as_dict=True,
            )
            if not module_doc:
                continue

            date_field = module_doc.get("transaction_date")
            date_field = date_field.strftime("%d-%m-%Y") if date_field else None

            if metric == "Value":
                order_value = flt(module_doc.get("total") or 0)
                total_amount += order_value
                order_value_display = fmt_money(order_value, currency=default_currency)
            else:
                order_value = flt(module_doc.get("total_qty") or 0)
                total_qty += order_value
                order_value_display = str(order_value)

            module_details.append(
                {
                    "customer_name": module_doc.customer_name,
                    "transaction_date": date_field,
                    "total_amount": fmt_money(
                        module_doc.total or 0, currency=default_currency
                    ),
                    "order_id": log.reference_docname,
                    "order_details": [
                        {"key": "Order ID", "value": log.reference_docname},
                        {"key": "Order Value", "value": order_value_display},
                        {"key": "Status", "value": module_doc.status},
                    ],
                }
            )

        card_details = [
            {"key": "Total Orders", "value": len(module_details)},
            {
                "key": "Total Amount" if metric == "Value" else "total_qty",
                "value": (
                    fmt_money(total_amount, currency=default_currency)
                    if metric == "Value"
                    else str(total_qty)
                ),
            },
        ]

        return gen_response(
            200,
            "Employee Target Order Details fetched successfully",
            {
                "card_details": card_details,
                "orders": module_details,
            },
        )

    except frappe.PermissionError:
        return gen_response(403, "Unauthorized to access this target")
    except Exception as e:
        return exception_handler(e)
