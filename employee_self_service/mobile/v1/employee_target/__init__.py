import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
)
from frappe.utils import flt, fmt_money, getdate
from datetime import datetime

# Cache for default currency
_default_currency_cache = None

def _get_default_currency():
    """Get default currency with caching."""
    global _default_currency_cache
    if _default_currency_cache is None:
        _default_currency_cache = frappe.get_cached_value("Global Defaults", None, "default_currency")
    return _default_currency_cache

def _format_date(date_value, format_str="%d-%m-%Y"):
    """Format date safely."""
    if not date_value:
        return None
    try:
        if isinstance(date_value, str):
            date_value = getdate(date_value)
        return date_value.strftime(format_str)
    except (AttributeError, ValueError, TypeError):
        return str(date_value) if date_value else None

def _format_currency_amount(amount, currency=None):
    """Format currency amount."""
    if currency is None:
        currency = _get_default_currency()
    return fmt_money(flt(amount) or 0.0, currency=currency)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_list(filters=None):
    """Fetch employee target entries."""
    try:
        # Get employee
        employee = get_employee_by_user(frappe.session.user)
        if not employee:
            return gen_response(500, "Employee not found for this user")

        # Build filters
        filters = []
        filters.append(["employee", "=", employee.get("name")])
        # Single database query
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
            order_by="creation desc"
        )

        if not target_list:
            return gen_response(200, "Employee Targets retrieved successfully", [])

        # Get currency once
        default_currency = _get_default_currency()
        
        # Process all records
        for target in target_list:
            # Format currency amounts
            target["total_target"] = _format_currency_amount(target.get("total_target"), default_currency)
            target["total_achieved"] = _format_currency_amount(target.get("total_achieved"), default_currency)
            # Format progress to 2 decimal places
            target["progress"] = round(flt(target.get("progress", 0)), 2)
            # Format dates
            target["start_date"] = _format_date(target.get("start_date"))
            target["end_date"] = _format_date(target.get("end_date"))

        return gen_response(200, "Employee Targets retrieved successfully", target_list)
    
    except frappe.PermissionError:
        return gen_response(403, "Unauthorized access to employee targets")
    except Exception as e:
        frappe.log_error(title="Error in get_employee_targets_list", message=frappe.get_traceback())
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_details(target_id=None):
    """Fetch detailed information for a specific employee target."""
    try:
        if not target_id:
            return gen_response(400, "Target ID is required")

        # Get target document
        try:
            target_doc = frappe.get_doc("Employee Target Entry", target_id)
        except frappe.DoesNotExistError:
            return gen_response(404, "Employee Target Entry not found")

        # Convert to dict
        target_data = target_doc.as_dict()
        
        # Get currency
        default_currency = _get_default_currency()

        # Format dates
        date_fields = ["start_date", "end_date"]
        for field in date_fields:
            target_data[field] = _format_date(target_data.get(field))

        # Format main amounts
        amount_fields = ["total_target", "total_achieved"]
        for field in amount_fields:
            target_data[field] = _format_currency_amount(target_data.get(field), default_currency)
        target_data["progress"] = round(flt(target_data.get("progress", 0)), 2)
        # Format child table amounts
        item_group_targets = target_data.get("item_group_wise_target", [])
        if item_group_targets:
            child_amount_fields = ["target", "achieved"]
            for item_group in item_group_targets:
                for field in child_amount_fields:
                    item_group[field] = _format_currency_amount(item_group.get(field), default_currency)

        return gen_response(200, "Employee Target Details retrieved successfully", target_data)
    
    except frappe.PermissionError:
        return gen_response(403, "Unauthorized to access this target")
    except Exception as e:
        frappe.log_error(title="Error in get_employee_target_details", message=frappe.get_traceback())
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_employee_target_order_details(target_id=None):
    """Fetch order details for a specific employee target."""
    try:
        if not target_id:
            return gen_response(400, "Target ID is required")

        # Get target logs - using SP Target Log data directly
        target_logs = frappe.get_all(
            "SP Target Log",
            filters={"employee_target_entry": target_id},
            fields=[
                "reference_doctype", 
                "reference_docname", 
                "metric",
                "customer_name",
                "transaction_date",
                "amount",
                "total_qty",
                "status",
                "item_group"
            ]
        )

        if not target_logs:
            return gen_response(404, "No target order/invoice found for the given Target ID")

        # Get metric from first log
        metric = target_logs[0].metric

        # Get currency
        default_currency = _get_default_currency()
        
        # Build response data directly from SP Target Log
        module_details = []
        total_amount = total_qty = 0

        for log in target_logs:
            # Skip cancelled entries if status indicates so
            if log.get("status") == "Cancelled":
                continue

            # Format date
            formatted_date = _format_date(log.get("transaction_date"))
            
            # Calculate order value based on metric
            if metric == "Value":
                order_value = flt(log.get("amount", 0))
                total_amount += order_value
                order_value_display = _format_currency_amount(order_value, default_currency)
            else:
                order_value = flt(log.get("total_qty", 0))
                total_qty += order_value
                order_value_display = str(int(order_value)) if order_value.is_integer() else str(order_value)

            # Build order details using SP Target Log data
            module_details.append({
                "customer_name": log.get("customer_name"),
                "transaction_date": formatted_date,
                "total_amount": _format_currency_amount(log.get("amount", 0), default_currency),
                "order_id": log.get("reference_docname"),
                "order_details": [
                    {"key": "Order ID", "value": log.get("reference_docname")},
                    {"key": "Order Value", "value": order_value_display},
                    {"key": "Item Group", "value": log.get("item_group", "")},
                ],
            })

        # Build card details
        total_orders = len(module_details)
        total_value_display = (
            _format_currency_amount(total_amount, default_currency) 
            if metric == "Value" 
            else str(int(total_qty)) if total_qty and total_qty.is_integer() else str(total_qty)
        )

        card_details = [
            {"key": "Total Orders", "value": total_orders},
            {
                "key": "Total Amount" if metric == "Value" else "Total Qty",
                "value": total_value_display,
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
        frappe.log_error(title="Error in get_employee_target_order_details", message=frappe.get_traceback())
        return exception_handler(e)
