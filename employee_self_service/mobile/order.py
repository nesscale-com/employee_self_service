import json
import frappe
from frappe import _

from erpnext.accounts.utils import getdate
from employee_self_service.mobile.api_utils import (
    gen_response,
    ess_validate,
    get_ess_settings,
    prepare_json_data,
    get_global_defaults,
    exception_handel,
)
from erpnext.accounts.party import get_dashboard_info

"""order list api for mobile app"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_order_list():
    try:
        order_list = frappe.get_list(
            "Sales Order",
            fields=[
                "name",
                "customer_name",
                "DATE_FORMAT(transaction_date, '%d-%m-%Y') as transaction_date",
                "grand_total",
                "workflow_state as status",
                "total_qty",
            ],
        )
        gen_response(200, "Order list get successfully", order_list)
    except Exception as e:
        return exception_handel(e)


"""get order details for mobile app"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_order(*args, **kwargs):
    try:
        data = kwargs
        order_doc = json.loads(
            frappe.get_doc("Sales Order", data.get("order_id")).as_json()
        )
        transaction_date = getdate(order_doc["transaction_date"])
        delivery_date = getdate(order_doc["delivery_date"])
        order_doc["transaction_date"] = transaction_date.strftime("%d-%m-%Y")
        order_doc["delivery_date"] = delivery_date.strftime("%d-%m-%Y")
        order_data = prepare_json_data(
            [
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
                "total_taxes_and_charges",
                "net_total",
                "discount_amount",
                "grand_total",
            ],
            order_doc,
        )
        item_list = []
        for item in order_doc.get("items"):
            item_list.append(
                prepare_json_data(
                    [
                        "item_name",
                        "item_code",
                        "qty",
                        "amount",
                        "rate",
                        "image",
                    ],
                    item,
                )
            )
        order_data["items"] = item_list
        order_data["next_action"] = get_actions(order_doc)
        order_data["allow_edit"] = True
        order_data["created_by"] = frappe.get_cached_value(
            "User", order_doc.get("owner"), "full_name"
        )
        dashboard_info = get_dashboard_info("Customer", order_doc.get("customer"))
        order_data["annual_billing"] = (
            dashboard_info[0].get("billing_this_year") if dashboard_info else 0.0
        )
        order_data["total_unpaid"] = (
            dashboard_info[0].get("total_unpaid") if dashboard_info else 0.0
        )
        gen_response(200, "Order detail get successfully.", order_data)
    except Exception as e:
        return exception_handel(e)


"""get the workflow action"""


def get_actions(order_doc):
    from frappe.model.workflow import get_transitions

    transitions = get_transitions(order_doc)
    actions = []
    for row in transitions:
        actions.append(row.get("action"))
    return actions


"""update the workflow state of order"""


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_workflow_state(order_id, action):
    try:
        from frappe.model.workflow import apply_workflow

        order_doc = frappe.get_doc("Sales Order", order_id)
        apply_workflow(order_doc, action)
        return gen_response(200, "Order Workflow State Updated Successfully")
    except Exception as e:
        return exception_handel(e)


"""get customer list for mobile app to make order"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_customer_list():
    try:
        customer_list = frappe.get_list(
            "Customer",
            fields=["name", "customer_name", "phone"],
        )
        gen_response(200, "Customer list get successfully", customer_list)
    except Exception as e:
        return exception_handel(e)


"""get item list for mobile app to make order"""


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
    except Exception as e:
        exception_handel(e)


def get_items_rate(items):
    ess_settings = get_ess_settings()
    price_list = ess_settings.get("default_price_list")
    for item in items:
        item_price = frappe.get_all(
            "Item Price",
            filters={"item_code": item.name, "price_list": price_list},
            fields=["price_list_rate"],
        )
        if item_price:
            item["rate"] = item_price[0].price_list_rate or 0
        else:
            item["rate"] = 0.0
    return items


"""this used to calculate the order calculations"""


@frappe.whitelist()
@ess_validate(methods=["POST"])
def prepare_order_totals(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("customer"):
            return gen_response(500, "Customer is required.")

        ess_settings = get_ess_settings()
        default_warehouse = ess_settings.get("default_warehouse")
        delivery_date = data.get("delivery_date")
        for item in data.get("items"):
            item["delivery_date"] = delivery_date
            item["warehouse"] = default_warehouse
        global_defaults = get_global_defaults()
        company = global_defaults.get("default_company")
        sales_order_doc = frappe.get_doc(dict(doctype="Sales Order", company=company))
        sales_order_doc.update(data)
        sales_order_doc.run_method("set_missing_values")
        sales_order_doc.run_method("calculate_taxes_and_totals")
        order_data = (
            prepare_json_data(
                [
                    "total_taxes_and_charges",
                    "net_total",
                    "discount_amount",
                    "grand_total",
                ],
                json.loads(sales_order_doc.as_json()),
            ),
        )
        gen_response(200, "Order details get successfully", order_data)
    except Exception as e:
        return exception_handel(e)


"""create order api"""


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
        company = global_defaults.get("default_company")
        ess_settings = get_ess_settings()
        default_warehouse = ess_settings.get("default_warehouse")

        if data.get("order_id"):
            if not frappe.db.exists("Sales Order", data.get("order_id"), cache=True):
                return gen_response(500, "Invalid order id.")
            sales_order_doc = frappe.get_doc("Sales Order", data.get("order_id"))
            delivery_date = data.get("delivery_date")
            for item in data.get("items"):
                item["delivery_date"] = delivery_date
                item["warehouse"] = default_warehouse
            sales_order_doc.update(data)
            sales_order_doc.run_method("set_missing_values")
            sales_order_doc.run_method("calculate_taxes_and_totals")
            sales_order_doc.save()
            gen_response(200, "Order updated successfully.", sales_order_doc.name)
        else:
            sales_order_doc = frappe.get_doc(
                dict(doctype="Sales Order", company=company)
            )
            delivery_date = data.get("delivery_date")
            for item in data.get("items"):
                item["delivery_date"] = delivery_date
                item["warehouse"] = default_warehouse
            sales_order_doc.update(data)
            sales_order_doc.run_method("set_missing_values")
            sales_order_doc.run_method("calculate_taxes_and_totals")
            sales_order_doc.insert()

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

    except Exception as e:
        return exception_handel(e)
