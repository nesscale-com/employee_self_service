import json
from datetime import datetime

import frappe
from erpnext.accounts.party import get_dashboard_info
from erpnext.accounts.utils import getdate
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
    prepare_json_data,
)

"""purchase order list api for mobile app"""


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
    schedule_date_type=None,
    schedule_date_from=None,
    schedule_date_to=None,
):
    try:
        if isinstance(filters, str):
            filters = frappe.parse_json(filters)

        global_defaults = get_global_defaults()
        status_field = check_workflow_exists("Purchase Order") or "status"

        if posting_date_type and not posting_date_type == "Custom Date":
            posting_duration_details = get_date_range(posting_date_type)
            posting_date_from = posting_duration_details.get("from_date")
            posting_date_to = posting_duration_details.get("to_date")

        if schedule_date_type and not schedule_date_type == "Custom Date":
            schedule_duration_details = get_date_range(schedule_date_type)
            schedule_date_from = schedule_duration_details.get("from_date")
            schedule_date_to = schedule_duration_details.get("to_date")

        # Move 'status' into dynamic status field
        if filters and filters.get("status"):
            filters[status_field] = filters.pop("status")

        # Handle 'item' filter separately (joins with Sales Order Item)
        updated_filters = []

        if filters:
            for key, value in filters.items():
                if key == "item_name":
                    updated_filters.append(
                        ["Purchase Order Item", "item_code", "=", value]
                    )
                else:
                    updated_filters.append(["Purchase Order", key, "=", value])

        if posting_date_type and posting_date_from and posting_date_to:
            updated_filters.append(
                [
                    "Purchase Order",
                    "transaction_date",
                    "Between",
                    [posting_date_from, posting_date_to],
                ]
            )
        if schedule_date_type and schedule_date_from and schedule_date_to:
            updated_filters.append(
                [
                    "Purchase Order",
                    "schedule_date",
                    "Between",
                    [schedule_date_from, schedule_date_to],
                ]
            )

        order_list = frappe.get_list(
            "Purchase Order",
            fields=[
                "name",
                "supplier",
                "supplier_name",
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
        return gen_response(403, "Not permitted for Purchase Order")

    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_order_status():
    try:
        # Get status options from Purchase Order doctype meta
        meta = frappe.get_meta("Purchase Order")
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
            frappe.get_doc("Purchase Order", data.get("order_id")).as_json()
        )
        global_defaults = get_global_defaults()
        transaction_date = getdate(order_doc["transaction_date"])
        schedule_date = getdate(order_doc["schedule_date"])
        order_doc["transaction_date"] = transaction_date.strftime("%d-%m-%Y")
        order_doc["schedule_date"] = schedule_date.strftime("%d-%m-%Y")
        order_data = get_order_details_with_currency(
            order_doc, global_defaults.get("default_currency")
        )
        for response_field in [
            "name",
            "supplier",
            "transaction_date",
            "schedule_date",
            "workflow_state",
            "total_qty",
            "supplier_name",
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
        dashboard_info = get_dashboard_info("supplier", order_doc.get("supplier"))
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
        return gen_response(500, "Not permitted for Purchase order")
    except Exception as e:
        return exception_handler(e)


def get_attachments(id):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Purchase Order", "attached_to_name": id},
        fields=["name", "file_url", "file_name"],
    )

@frappe.whitelist()
@ess_validate(methods=["POST"])
def prepare_order_totals(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("supplier"):
            return gen_response(500, "supplier is required.")
        ess_settings = get_ess_settings()
        for item in data.get("items"):
            item["schedule_date"] = data.get("schedule_date")
            item["warehouse"] = ess_settings.get("default_warehouse")
        global_defaults = get_global_defaults()
        purchase_order_doc = frappe.get_doc(
            doctype="Purchase Order", company=global_defaults.get("default_company")
        )
        purchase_order_doc.update(data)
        purchase_order_doc.apply_discount_on = "Grand Total"

        purchase_order_doc.run_method("set_missing_values")
        purchase_order_doc.run_method("calculate_taxes_and_totals")
        purchase_order_doc = json.loads(purchase_order_doc.as_json())
        gen_response(
            200,
            "Order details get successfully",
            get_order_details_with_currency(
                purchase_order_doc, global_defaults.get("default_currency")
            ),
        )
    except Exception as e:
        return exception_handler(e)


def get_order_details_with_currency(purchase_order_doc, currency):
    order_response_dict = {}
    for response_fields in [
        "total_taxes_and_charges",
        "net_total",
        "discount_amount",
        "grand_total",
        "total",
    ]:
        order_response_dict[response_fields] = fmt_money(
            purchase_order_doc.get(response_fields),
            currency=currency,
        )
    return order_response_dict


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_order(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("supplier"):
            return gen_response(500, "supplier is required.")
        if not data.get("items") or len(data.get("items")) == 0:
            return gen_response(500, "Please select items to proceed.")
        if not data.get("schedule_date"):
            return gen_response(500, "Please select schedule date to proceed.")
        global_defaults = get_global_defaults()
        # ess_settings = get_ess_settings()
        if data.get("order_id"):
            if not frappe.db.exists("Purchase Order", data.get("order_id"), cache=True):
                return gen_response(500, "Invalid order id.")
            purchase_order_doc = frappe.get_doc("Purchase Order", data.get("order_id"))
            _create_update_order(
                data=data,
                purchase_order_doc=purchase_order_doc,
                default_warehouse=data.get("set_warehouse"),
            )
            if data.get("attachments") is not None:
                for file in data.get("attachments"):
                    file_doc = frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_url": file.get("file_url"),
                            "attached_to_doctype": "Purchase Order",
                            "attached_to_name": purchase_order_doc.name,
                        }
                    )
                    file_doc.insert(ignore_permissions=True)
            gen_response(200, "Order updated successfully.", purchase_order_doc.name)
        else:
            purchase_order_doc = frappe.get_doc(
                doctype="Purchase Order",
                company=global_defaults.get("default_company"),
            )
            _create_update_order(
                data=data,
                purchase_order_doc=purchase_order_doc,
                default_warehouse=data.get("set_warehouse"),
            )
            if data.get("attachments") is not None:
                for file in data.get("attachments"):
                    file_doc = frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_url": file.get("file_url"),
                            "attached_to_doctype": "Purchase Order",
                            "attached_to_name": purchase_order_doc.name,
                        }
                    )
                    file_doc.insert(ignore_permissions=True)

            gen_response(200, "Order created successfully.", purchase_order_doc.name)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for create purchase order")
    except Exception as e:
        return exception_handler(e)


def _create_update_order(data, purchase_order_doc, default_warehouse):
    schedule_date = data.get("schedule_date")
    for item in data.get("items"):
        item["schedule_date"] = schedule_date
        item["warehouse"] = default_warehouse
    purchase_order_doc.apply_discount_on = "Grand Total"
    purchase_order_doc.update(data)
    purchase_order_doc.run_method("set_missing_values")
    purchase_order_doc.run_method("calculate_taxes_and_totals")
    purchase_order_doc.save()
    
    
@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_supplier_list(start=0, page_length=10, filters=None):
    try:
        supplier_list = frappe.get_list(
            "Supplier",
            fields=["name", "supplier_name", "mobile_no as phone"],
            start=start,
            filters=filters,
            page_length=page_length,
            order_by="modified desc",
        )
        gen_response(200, "Supplier list get successfully", supplier_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for supplier")
    except Exception as e:
        return exception_handler(e)