import json
from datetime import datetime

import frappe
from erpnext.accounts.party import get_dashboard_info
from erpnext.accounts.utils import getdate
from erpnext.stock.utils import get_stock_balance
from frappe import _
from frappe.utils import fmt_money

from employee_self_service.mobile.v1.api_utils import (
    check_workflow_exists,
    ess_validate,
    exception_handler,
    gen_response,
    get_actions,
    get_date_range,
    get_ess_settings,
    get_global_defaults,
    get_sales_person_by_customer,
    prepare_json_data,
)

"""order list api for mobile app"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_order_list(
    start=0,
    page_length=10,
    order_by="modified",
    sort_order="desc",
    filters=None,
    posting_date_type=None,
    posting_date_from=None,
    posting_date_to=None,
    delivery_date_type=None,
    delivery_date_from=None,
    delivery_date_to=None,
):
    try:
        if isinstance(filters, str):
            filters = frappe.parse_json(filters)
        frappe.log_error(title="Filters for order list", message=str(filters))
        global_defaults = get_global_defaults()
        status_field = check_workflow_exists("Sales Order") or "status"

        if posting_date_type and not posting_date_type == "Custom Date":
            posting_duration_details = get_date_range(posting_date_type)
            posting_date_from = posting_duration_details.get("from_date")
            posting_date_to = posting_duration_details.get("to_date")

        if delivery_date_type and not delivery_date_type == "Custom Date":
            delivery_duration_details = get_date_range(delivery_date_type)
            delivery_date_from = delivery_duration_details.get("from_date")
            delivery_date_to = delivery_duration_details.get("to_date")

        # Move 'status' into dynamic status field
        if filters and filters.get("status"):
            filters[status_field] = filters.pop("status")

        # Handle 'item' filter separately (joins with Sales Order Item)
        updated_filters = []

        if filters:
            for key, value in filters.items():
                if key == "item_name":
                    updated_filters.append(
                        ["Sales Order Item", "item_code", "=", value]
                    )
                elif isinstance(value, list) and len(value) == 2:
                    updated_filters.append(["Sales Order", key, value[0], value[1]])
                else:
                    updated_filters.append(["Sales Order", key, "=", value])

        if posting_date_type and posting_date_from and posting_date_to:
            updated_filters.append(
                [
                    "Sales Order",
                    "transaction_date",
                    "Between",
                    [posting_date_from, posting_date_to],
                ]
            )
        if delivery_date_type and delivery_date_from and delivery_date_to:
            updated_filters.append(
                [
                    "Sales Order",
                    "delivery_date",
                    "Between",
                    [delivery_date_from, delivery_date_to],
                ]
            )

        order_list = frappe.get_list(
            "Sales Order",
            fields=[
                "name",
                "customer",
                "customer_name",
                "transaction_date",
                "grand_total",
                f"{status_field} as status",
                "total_qty",
            ],
            start=start,
            page_length=page_length,
            order_by=f"{order_by} {sort_order}",
            filters=updated_filters,
        )

        for order in order_list:
            order["grand_total"] = fmt_money(
                order["grand_total"], currency=global_defaults.get("default_currency")
            )
            order["transaction_date"] = datetime.strftime(
                order["transaction_date"], "%d-%m-%Y"
            )

        return gen_response(200, "Order list fetched successfully", order_list)

    except frappe.PermissionError:
        return gen_response(403, "Not permitted for Sales Order")

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
def get_order_status():
    try:
        # Get status options from Sales Order doctype meta
        meta = frappe.get_meta("Sales Order")
        status_field_meta = meta.get_field("status")
        status_options = []

        if status_field_meta and status_field_meta.options:
            # Remove empty/blank options
            status_options = [
                opt.strip()
                for opt in status_field_meta.options.split("\n")
                if opt.strip()
            ]

        return gen_response(
            200,
            "Order status options fetched successfully",
            status_options,
        )

    except Exception as e:
        return exception_handler(e)


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
            "customer",
            "transaction_date",
            "delivery_date",
            "workflow_state",
            "total_qty",
            "customer_name",
            "shipping_address",
            "contact_email",
            "contact_mobile",
            "contact_phone",
            "cost_center",
            "company",
            "set_warehouse",
            "discount_amount",
            "po_no",
            "project",
            "order_type",
            "commission_rate",
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
            item["price_list_rate_currency"] = fmt_money(
                item.get("price_list_rate"),
                currency=global_defaults.get("default_currency"),
            )
            if item.get("price_list_rate") == 0:
                item["price_list_rate"] = item.get("rate")
                item["price_list_rate_currency"] = fmt_money(
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
                        "discount_amount",
                        "discount_percentage",
                        "price_list_rate",
                        "price_list_rate_currency",
                        "uom",
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
        order_data["discount"] = order_data["discount_amount"]
        order_data["discount_amount"] = fmt_money(
            order_data["discount_amount"] if order_data["discount_amount"] else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        order_data["attachments"] = get_attachments(data.get("order_id"))
        gen_response(200, "Order detail get successfully.", order_data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for sales order")
    except Exception as e:
        return exception_handler(e)


def get_attachments(id):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Sales Order", "attached_to_name": id},
        fields=["name", "file_url", "file_name"],
    )


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
def get_item_list(
    start=0,
    page_length=10,
    filters=None,
    customer=None,
    for_filters=None,
    or_filters=None,
    warehouse=None,
):
    try:
        if not filters:
            filters = []
        filters.append(["Item", "show_in_mobile", "=", 1])
        item_list = frappe.get_list(
            "Item",
            fields=["name", "item_name", "item_code", "image", "sales_uom", "stock_uom"],
            filters=filters,
            start=start,
            or_filters=or_filters,
            page_length=page_length,
        )
        for item in item_list:
            item["uom"] = item.get("sales_uom") or item.get("stock_uom")
        if for_filters:
            items = item_list
        else:
            items = get_items_rate(item_list, customer=customer, warehouse=warehouse)
        gen_response(200, "Item list get successfully", items)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for item")
    except Exception as e:
        exception_handler(e)


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


def _get_item_price(item_code, price_list, uom):
    item_price = frappe.db.get_value(
        "Item Price",
        {"price_list": price_list, "item_code": item_code, "uom": uom},
        "price_list_rate",
        order_by="valid_from desc",
    )
    return item_price or 0.0


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_uoms(customer, item):
    try:
        global_defaults = get_global_defaults()
        sales_price_list = get_default_price_list(customer=customer)
        item_doc = frappe.get_doc("Item", item)
        default_uom = item_doc.get("sales_uom") or item_doc.get("stock_uom")
        stock_uom = item_doc.get("stock_uom")
        uoms = []
        default_uom_price = _get_item_price(
            item_code=item_doc.get("name"),
            price_list=sales_price_list,
            uom=default_uom,
        )
        for uom_row in item_doc.get("uoms"):
            uom_hint = f"1 {uom_row.get('uom')} = {uom_row.get('conversion_factor')} {stock_uom}"
            uom_details = dict(
                uom=uom_row.get("uom"),
                conversion_factor=uom_row.get("conversion_factor"),
                uom_hint=uom_hint,
                is_default=uom_row.get("uom") == default_uom,
            )
            get_uom_item_price(
                sales_price_list, item, uom_details, default_uom_price, global_defaults
            )
            uoms.append(uom_details)
        # Put sales_uom first in the list
        uoms.sort(key=lambda u: u["uom"] != default_uom)
        return gen_response(200, "uom details get successfully", uoms)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for item")
    except Exception as e:
        exception_handler(e)


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


@frappe.whitelist()
def scan_item(barcode):
    try:
        from erpnext.stock.utils import scan_barcode

        item_details = scan_barcode(barcode)
        item_list = frappe.get_list(
            "Item",
            filters={"name": item_details.get("item_code")},
            fields=["name", "item_name", "item_code", "image", "sales_uom", "stock_uom"],
        )
        for item in item_list:
            item["uom"] = item.get("sales_uom") or item.get("stock_uom")
        items = get_items_rate(item_list)
        if len(items) >= 1:
            gen_response(200, "Item list get successfully", items[0])
        else:
            gen_response(500, "Item does not exists")
    except Exception as e:
        return exception_handler(e)


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
            doctype="Sales Order", company=global_defaults.get("default_company")
        )
        sales_order_doc.update(data)
        sales_order_doc.apply_discount_on = "Grand Total"

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
        "total",
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
        # ess_settings = get_ess_settings()
        if data.get("order_id"):
            if not frappe.db.exists("Sales Order", data.get("order_id"), cache=True):
                return gen_response(500, "Invalid order id.")
            sales_order_doc = frappe.get_doc("Sales Order", data.get("order_id"))
            _create_update_order(
                data=data,
                sales_order_doc=sales_order_doc,
                default_warehouse=data.get("set_warehouse"),
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
            gen_response(200, "Order updated successfully.", sales_order_doc.name)
        else:
            sales_order_doc = frappe.get_doc(
                doctype="Sales Order",
                company=global_defaults.get("default_company"),
            )
            _create_update_order(
                data=data,
                sales_order_doc=sales_order_doc,
                default_warehouse=data.get("set_warehouse"),
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


@frappe.whitelist()
@ess_validate(methods=["GET", "POST"])
def get_item_group_list(filters=None):
    try:
        if not filters:
            filters = []
        filters.append(["Item Group", "show_in_mobile", "=", 1])
        item_group_list = frappe.get_list(
            "Item Group", fields=["name"], filters=filters
        )
        gen_response(200, "Item group list get successfully", item_group_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for item")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_warehouse_list(filters=None):
    try:
        if not filters:
            filters = []
        filters.append(["Warehouse", "is_group", "=", 0])
        item_group_list = frappe.get_list("Warehouse", fields=["name"], filters=filters)
        gen_response(200, "Warehouse list get successfully", item_group_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for item")
    except Exception as e:
        return exception_handler(e)
