import json
import frappe
from frappe import _
from frappe.utils import cstr, fmt_money

from erpnext.accounts.utils import getdate
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    get_ess_settings,
    prepare_json_data,
    get_global_defaults,
    exception_handler,
    get_actions,
    check_workflow_exists,
)
from erpnext.accounts.party import get_dashboard_info

"""order list api for mobile app"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_order_list(start=0, page_length=10, filters=None):
    try:
        global_defaults = get_global_defaults()
        status_field = check_workflow_exists("Sales Order")
        if status_field == False:
            status_field = "status"
        if filters and filters.get("status"):
            status_val = filters.get("status")
            del filters["status"]
            filters[status_field] = status_val
        order_list = frappe.get_list(
            "Sales Order",
            fields=[
                "name",
                "customer_name",
                "DATE_FORMAT(transaction_date, '%d-%m-%Y') as transaction_date",
                "grand_total",
                f"{status_field} as status",
                "total_qty",
            ],
            start=start,
            page_length=page_length,
            order_by="modified desc",
            filters=filters,
        )
        for order in order_list:
            order["grand_total"] = fmt_money(
                order["grand_total"], currency=global_defaults.get("default_currency")
            )
        gen_response(200, "Order list get successfully", order_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for sales order")
    except Exception as e:
        return exception_handler(e)


# def check_workflow_exists():
#     sales_order_workflow = frappe.get_all(
#         "Workflow",
#         filters={"document_type": "Sales Order", "is_active": 1},
#         fields=["workflow_state_field"],
#     )
#     if sales_order_workflow:
#         return sales_order_workflow[0].workflow_state_field
#     else:
#         return False


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_order(*args, **kwargs):
    try:
        data = kwargs
        order_doc = json.loads(
            frappe.get_doc("Sales Order", data.get("order_id")).as_json()
        )
        global_defaults = get_global_defaults()
        transaction_date = getdate(order_doc["transaction_date"])
        delivery_date = getdate(order_doc["delivery_date"])
        order_doc["transaction_date"] = transaction_date.strftime("%d-%m-%Y")
        order_doc["delivery_date"] = delivery_date.strftime("%d-%m-%Y")
        order_data = get_order_details_with_currency(
            order_doc, global_defaults.get("default_currency")
        )
        for response_field in [
            "name",
            "transaction_date",
            "delivery_date",
            "workflow_state",
            "total_qty",
            "customer_name",
            "shipping_address",
            "contact_email",
            "contact_mobile",
            "contact_phone",
        ]:
            order_data[response_field] = order_doc.get(response_field)
        item_list = []
        for item in order_doc.get("items"):
            item["amount"] = fmt_money(
                item.get("amount"), currency=global_defaults.get("default_currency")
            )
            item["rate_currency"] = fmt_money(
                item.get("rate"), currency=global_defaults.get("default_currency")
            )
            item_list.append(
                prepare_json_data(
                    [
                        "item_name",
                        "item_code",
                        "qty",
                        "amount",
                        "rate",
                        "image",
                        "rate_currency",
                    ],
                    item,
                )
            )
        order_data["items"] = item_list
        order_data["next_action"] = get_actions(order_doc, order_data)
        order_data["allow_edit"] = True if order_doc.get("docstatus") == 0 else False
        order_data["created_by"] = frappe.get_cached_value(
            "User", order_doc.get("owner"), "full_name"
        )
        dashboard_info = get_dashboard_info("Customer", order_doc.get("customer"))
        order_data["annual_billing"] = fmt_money(
            dashboard_info[0].get("billing_this_year") if dashboard_info else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        order_data["total_unpaid"] = fmt_money(
            dashboard_info[0].get("total_unpaid") if dashboard_info else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        gen_response(200, "Order detail get successfully.", order_data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for sales order")
    except Exception as e:
        return exception_handler(e)


# def get_actions(doc, doc_data=None):
#     from frappe.model.workflow import get_transitions

#     if not check_workflow_exists():
#         doc_data["workflow_state"] = doc.get("status")
#         return []
#     transitions = get_transitions(doc)
#     actions = []
#     for row in transitions:
#         actions.append(row.get("action"))
#     return actions


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_workflow_state(order_id, action):
    try:
        from frappe.model.workflow import apply_workflow

        order_doc = frappe.get_doc("Sales Order", order_id)
        apply_workflow(order_doc, action)
        return gen_response(200, "Order Workflow State Updated Successfully")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_customer_list(start=0, page_length=10, filters=None):
    try:
        customer_list = frappe.get_list(
            "Customer",
            fields=["name", "customer_name", "mobile_no as phone"],
            start=start,
            filters=filters,
            page_length=page_length,
            order_by="modified desc",
        )
        gen_response(200, "Customer list get successfully", customer_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for customer")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_item_list():
    try:
        item_list = frappe.get_list(
            "Item",
            fields=["name", "item_name", "item_code", "image"],
        )
        items = get_items_rate(item_list)
        gen_response(200, "Item list get successfully", items)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for item")
    except Exception as e:
        exception_handler(e)


def get_items_rate(items):
    global_defaults = get_global_defaults()
    ess_settings = get_ess_settings()
    price_list = ess_settings.get("default_price_list")
    if not price_list:
        frappe.throw(_("Please set price list in ess settings."))
    for item in items:
        item_price = frappe.get_all(
            "Item Price",
            filters={"item_code": item.name, "price_list": price_list},
            fields=["price_list_rate"],
        )
        item["rate_currency"] = fmt_money(
            item_price[0].price_list_rate if item_price else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        item["rate"] = item_price[0].price_list_rate if item_price else 0.0
    return items


@frappe.whitelist()
@ess_validate(methods=["POST"])
def prepare_order_totals(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("customer"):
            return gen_response(500, "Customer is required.")
        ess_settings = get_ess_settings()
        for item in data.get("items"):
            item["delivery_date"] = data.get("delivery_date")
            item["warehouse"] = ess_settings.get("default_warehouse")
        global_defaults = get_global_defaults()
        sales_order_doc = frappe.get_doc(
            dict(doctype="Sales Order", company=global_defaults.get("default_company"))
        )
        sales_order_doc.update(data)
        sales_order_doc.run_method("set_missing_values")
        sales_order_doc.run_method("calculate_taxes_and_totals")
        sales_order_doc = json.loads(sales_order_doc.as_json())
        gen_response(
            200,
            "Order details get successfully",
            get_order_details_with_currency(
                sales_order_doc, global_defaults.get("default_currency")
            ),
        )
    except Exception as e:
        return exception_handler(e)


def get_order_details_with_currency(sales_order_doc, currency):
    order_response_dict = {}
    for response_fields in [
        "total_taxes_and_charges",
        "net_total",
        "discount_amount",
        "grand_total",
    ]:
        order_response_dict[response_fields] = fmt_money(
            sales_order_doc.get(response_fields),
            currency=currency,
        )
    return order_response_dict


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_order(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("customer"):
            return gen_response(500, "Customer is required.")
        if not data.get("items") or len(data.get("items")) == 0:
            return gen_response(500, "Please select items to proceed.")
        if not data.get("delivery_date"):
            return gen_response(500, "Please select delivery date to proceed.")
        global_defaults = get_global_defaults()
        ess_settings = get_ess_settings()
        if data.get("order_id"):
            if not frappe.db.exists("Sales Order", data.get("order_id"), cache=True):
                return gen_response(500, "Invalid order id.")
            sales_order_doc = frappe.get_doc("Sales Order", data.get("order_id"))
            _create_update_order(
                data=data,
                sales_order_doc=sales_order_doc,
                default_warehouse=ess_settings.get("default_warehouse"),
            )
            gen_response(200, "Order updated successfully.", sales_order_doc.name)
        else:
            sales_order_doc = frappe.get_doc(
                dict(
                    doctype="Sales Order",
                    company=global_defaults.get("default_company"),
                )
            )
            _create_update_order(
                data=data,
                sales_order_doc=sales_order_doc,
                default_warehouse=ess_settings.get("default_warehouse"),
            )
            if data.get("attachments") is not None:
                for file in data.get("attachments"):
                    file_doc = frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_url": file.get("file_url"),
                            "attached_to_doctype": "Sales Order",
                            "attached_to_name": sales_order_doc.name,
                        }
                    )
                    file_doc.insert(ignore_permissions=True)

            gen_response(200, "Order created successfully.", sales_order_doc.name)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for create sales order")
    except Exception as e:
        return exception_handler(e)


def _create_update_order(data, sales_order_doc, default_warehouse):
    delivery_date = data.get("delivery_date")
    for item in data.get("items"):
        item["delivery_date"] = delivery_date
        item["warehouse"] = default_warehouse
    sales_order_doc.update(data)
    sales_order_doc.run_method("set_missing_values")
    sales_order_doc.run_method("calculate_taxes_and_totals")
    sales_order_doc.save()
