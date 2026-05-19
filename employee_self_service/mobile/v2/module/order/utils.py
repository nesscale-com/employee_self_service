import frappe
from frappe import _ 
from frappe.utils import fmt_money
from erpnext.stock.utils import get_stock_balance
from employee_self_service.mobile.v2.utils import (
    get_global_defaults,
    get_ess_settings,
    get_sales_person_by_customer
)

def get_order_details_with_currency(sales_order_doc, currency):
    order_response_dict = {}
    for response_fields in [
        "total_taxes_and_charges",
        "net_total",
        "discount_amount",
        "grand_total",
        "total",
    ]:
        order_response_dict[response_fields] = fmt_money(
            sales_order_doc.get(response_fields),
            currency=currency,
        )
    return order_response_dict

def get_items_rate(items, customer=None, warehouse=None):
    global_defaults = get_global_defaults()
    ess_settings = get_ess_settings()
    price_list = get_default_price_list(customer=customer)
    if not price_list:
        frappe.throw(
            _(
                "Please set a price list for the customer or define a default in the Selling Settings."
            )
        )

    # Check if stock balance should be included
    show_stock_balance = ess_settings.get("show_stock_balance_in_item_list", 0)

    for item in items:
        uom = item.get("uom")
        item_price = _get_item_price(
            item_code=item.name,
            price_list=price_list,
            uom=uom,
        )
        item_price_currency = fmt_money(
            item_price if item_price else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        item["rate_currency"] = item_price_currency
        item["rate"] = item_price if item_price else 0.0
        item["price_list_rate"] = item_price if item_price else 0.0
        item["price_list_rate_currency"] = item_price_currency

        # Add stock balance if enabled and warehouse is provided
        if show_stock_balance and warehouse:
            stock_balance = get_stock_balance(item.name, warehouse)
            item["stock_balance"] = stock_balance
        elif show_stock_balance:
            # If no warehouse specified, show 0 or get from default warehouse
            default_warehouse = ess_settings.get("default_warehouse")
            if default_warehouse:
                stock_balance = get_stock_balance(item.name, default_warehouse)
                item["stock_balance"] = stock_balance
            else:
                item["stock_balance"] = 0.0

    return items

def _create_update_order(data, sales_order_doc, default_warehouse):
    enable_target_management = frappe.db.get_single_value(
        "ESS Target Settings", "enable_target_management"
    )
    delivery_date = data.get("delivery_date")
    for item in data.get("items"):
        item["delivery_date"] = delivery_date
        item["warehouse"] = default_warehouse
    sales_order_doc.apply_discount_on = "Grand Total"
    sales_order_doc.update(data)
    sales_order_doc.run_method("set_missing_values")
    sales_order_doc.run_method("calculate_taxes_and_totals")

    # Populate sales team from Customer if not already set
    if not sales_order_doc.get("sales_team"):
        sales_persons = get_sales_person_by_customer(data.get("customer"))
        if sales_persons:
            sales_order_doc.set("sales_team", sales_persons)

    if enable_target_management:
        sales_persons = get_sales_person_by_customer(data.get("customer"))
        if sales_persons:
            sales_order_doc.set("sales_team", sales_persons)

    sales_order_doc.save()

def get_default_price_list(customer=None):
    if customer:
        price_list, customer_group = frappe.db.get_value(
            "Customer", customer, ["default_price_list", "customer_group"]
        )
        if price_list:
            return price_list
        price_list = frappe.db.get_value(
            "Customer Group", customer_group, "default_price_list"
        )
        if price_list:
            return price_list
    return frappe.db.get_single_value("Selling Settings", "selling_price_list")

def _get_item_price(item_code, price_list, uom):
    item_price = frappe.db.get_value(
        "Item Price",
        {"price_list": price_list, "item_code": item_code, "uom": uom},
        "price_list_rate",
        order_by="valid_from desc",
    )
    return item_price or 0.0

def get_uom_item_price(
    price_list, item_code, uom=None, default_uom_price=0.0, global_defaults=None
):
    item_price = _get_item_price(
        item_code=item_code,
        price_list=price_list,
        uom=uom.get("uom"),
    )
    if item_price:
        item_price_currency = fmt_money(
            item_price if item_price else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        uom["rate_currency"] = item_price_currency
        uom["rate"] = item_price if item_price else 0.0
        uom["price_list_rate"] = item_price if item_price else 0.0
        uom["price_list_rate_currency"] = item_price_currency
    else:
        item_price = default_uom_price * uom.get("conversion_factor")
        item_price_currency = fmt_money(
            item_price if item_price else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        uom["rate_currency"] = item_price_currency
        uom["rate"] = item_price if item_price else 0.0
        uom["price_list_rate"] = item_price if item_price else 0.0
        uom["price_list_rate_currency"] = item_price_currency

def get_attachments(id):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Sales Order", "attached_to_name": id},
        fields=["name", "file_url", "file_name"],
    )