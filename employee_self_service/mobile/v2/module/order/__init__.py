import frappe
import json
from frappe import _
from datetime import datetime
from erpnext.accounts.party import get_dashboard_info
from frappe.utils import fmt_money,getdate
from employee_self_service.mobile.v2.utils import (
    gen_response,
    exception_handler,
    ess_validate,
    get_global_defaults,
    check_workflow_exists,
    get_date_range,
    get_ess_settings,
    prepare_json_data,
    get_actions
)
from employee_self_service.mobile.v2.module.order.utils import (
    get_order_details_with_currency,
    get_items_rate,
    _create_update_order,
    _get_item_price,
    get_uom_item_price,
    get_default_price_list,
    get_attachments
)

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
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_warehouse_list(filters=None):
    try:
        if not filters:
            filters = []
        filters.append(["Warehouse", "is_group", "=", 0])
        item_group_list = frappe.get_list("Warehouse", fields=["name"], filters=filters)
        return gen_response(200, "Warehouse list get successfully", item_group_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for item")
    except Exception as e:
        return exception_handler(e)
    
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
        return exception_handler(e)
    
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