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
    get_employee_by_user,
)
from erpnext.accounts.party import get_dashboard_info

from employee_self_service.mobile.v1.ess import download_pdf
from employee_self_service.mobile.v1.order import get_default_price_list

"""order list api for mobile app"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_quotation_list(start=0, page_length=10, filters=None):
    try:
        global_defaults = get_global_defaults()
        quotation_list = frappe.get_list(
            "Quotation",
            fields=[
                "name",
                "customer_name",
                "DATE_FORMAT(transaction_date, '%d-%m-%Y') as transaction_date",
                "grand_total",
                "status",
                "total_qty",
            ],
            start=start,
            page_length=page_length,
            order_by="modified desc",
            filters=filters,
        )
        for quotation in quotation_list:
            quotation["grand_total"] = fmt_money(
                quotation["grand_total"],
                currency=global_defaults.get("default_currency"),
            )
        gen_response(200, "Quotation list get successfully", quotation_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Quotation")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_quotation(*args, **kwargs):
    try:
        data = kwargs
        quotation_doc = json.loads(
            frappe.get_doc("Quotation", data.get("id")).as_json()
        )
        global_defaults = get_global_defaults()
        transaction_date = getdate(quotation_doc["transaction_date"])
        valid_till = getdate(quotation_doc["valid_till"])
        quotation_doc["transaction_date"] = transaction_date.strftime("%d-%m-%Y")
        quotation_doc["valid_till"] = valid_till.strftime("%d-%m-%Y")
        quotation_data = get_order_details_with_currency(
            quotation_doc, global_defaults.get("default_currency")
        )
        for response_field in [
            "name",
            "quotation_to",
            "party_name",
            "transaction_date",
            "valid_till",
            "total_qty",
            "customer_name",
            "shipping_address",
            "contact_email",
            "contact_mobile",
            "company",
            "terms",
            "discount_amount",
        ]:
            quotation_data[response_field] = quotation_doc.get(response_field)
        item_list = []
        for item in quotation_doc.get("items"):
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
                    ],
                    item,
                )
            )
        quotation_data["items"] = item_list
        quotation_data["allow_edit"] = (
            True if quotation_doc.get("docstatus") == 0 else False
        )
        quotation_data["created_by"] = frappe.get_cached_value(
            "User", quotation_doc.get("owner"), "full_name"
        )
        dashboard_info = get_dashboard_info("Customer", quotation_doc.get("customer"))
        quotation_data["annual_billing"] = fmt_money(
            dashboard_info[0].get("billing_this_year") if dashboard_info else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        quotation_data["total_unpaid"] = fmt_money(
            dashboard_info[0].get("total_unpaid") if dashboard_info else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        quotation_data["discount"] = quotation_data["discount_amount"]
        quotation_data["discount_amount"] = fmt_money(
            (
                quotation_data["discount_amount"]
                if quotation_data["discount_amount"]
                else 0.0
            ),
            currency=global_defaults.get("default_currency"),
        )
        quotation_data["attachments"] = get_attachments(data.get("id"))
        gen_response(200, "Quotation detail get successfully.", quotation_data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for sales order")
    except Exception as e:
        return exception_handler(e)


def get_attachments(id):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Quotation", "attached_to_name": id},
        fields=["file_url", "file_name"],
    )


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


# @frappe.whitelist()
# @ess_validate(methods=["POST"])
# def update_workflow_state(order_id, action):
#     try:
#         from frappe.model.workflow import apply_workflow

#         order_doc = frappe.get_doc("Sales Order", order_id)
#         apply_workflow(order_doc, action)
#         return gen_response(200, "Order Workflow State Updated Successfully")
#     except Exception as e:
#         return exception_handler(e)


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
def get_item_list(filters=None):
    try:
        if not filters:
            filters = []
        filters.append(["Item", "show_in_mobile", "=", 1])
        item_list = frappe.get_list(
            "Item", fields=["name", "item_name", "item_code", "image"], filters=filters
        )
        items = get_items_rate(item_list)
        gen_response(200, "Item list get successfully", items)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for item")
    except Exception as e:
        exception_handler(e)


def get_items_rate(items, customer=None):
    global_defaults = get_global_defaults()
    price_list = get_default_price_list(customer=customer)
    if not price_list:
        frappe.throw(
            _(
                "Please set a price list for the customer or define a default in the Selling Settings."
            )
        )
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
        item["price_list_rate"] = item_price[0].price_list_rate
        item["price_list_rate_currency"] = fmt_money(
            item_price[0].price_list_rate if item_price else 0.0,
            currency=global_defaults.get("default_currency"),
        )
    return items


@frappe.whitelist()
def scan_item(barcode):
    try:
        from erpnext.stock.utils import scan_barcode

        item_details = scan_barcode(barcode)
        item_list = frappe.get_list(
            "Item",
            filters={"name": item_details.get("item_code")},
            fields=["name", "item_name", "item_code", "image"],
        )
        items = get_items_rate(item_list)
        if len(items) >= 1:
            gen_response(200, "Item list get successfully", items[0])
        else:
            gen_response(500, "Item does not exists")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def prepare_quotation_totals(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("customer"):
            return gen_response(500, "Customer is required.")
        ess_settings = get_ess_settings()
        # total_discount = 0
        for item in data.get("items"):
            item["valid_till"] = data.get("valid_till")
            item["warehouse"] = ess_settings.get("default_warehouse")
            # if item["discount_amount"]:
            #     total_discount = total_discount + (
            #         float(item["discount_amount"]) * item["qty"]
            #     )

        global_defaults = get_global_defaults()
        sales_order_doc = frappe.get_doc(
            dict(doctype="Quotation", company=global_defaults.get("default_company"))
        )
        sales_order_doc.update(data)
        # sales_order_doc.discount_amount = total_discount
        sales_order_doc.apply_discount_on = "Grand Total"
        sales_order_doc.run_method("set_missing_values")
        sales_order_doc.run_method("calculate_taxes_and_totals")
        sales_order_doc = json.loads(sales_order_doc.as_json())
        gen_response(
            200,
            "Quotation details get successfully",
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
def create_quotation(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("party_name"):
            return gen_response(500, "Customer is required.")
        if not data.get("items") or len(data.get("items")) == 0:
            return gen_response(500, "Please select items to proceed.")
        global_defaults = get_global_defaults()
        ess_settings = get_ess_settings()
        if data.get("id"):
            if not frappe.db.exists("Quotation", data.get("id"), cache=True):
                return gen_response(500, "Invalid id.")
            doc = frappe.get_doc("Quotation", data.get("id"))
            _create_update_quotation(
                data=data,
                quotation_doc=doc,
                default_warehouse=ess_settings.get("default_warehouse"),
            )
            if data.get("attachments") is not None:
                for file in data.get("attachments"):
                    file_doc = frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_url": file.get("file_url"),
                            "attached_to_doctype": "Quotation",
                            "attached_to_name": doc.name,
                        }
                    )
                    file_doc.insert(ignore_permissions=True)
            gen_response(200, "Updated successfully.", doc.name)
        else:
            doc = frappe.get_doc(
                dict(
                    doctype="Quotation",
                    company=global_defaults.get("default_company"),
                )
            )
            _create_update_quotation(
                data=data,
                quotation_doc=doc,
                default_warehouse=ess_settings.get("default_warehouse"),
            )
            if data.get("attachments") is not None:
                for file in data.get("attachments"):
                    file_doc = frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_url": file.get("file_url"),
                            "attached_to_doctype": "Quotation",
                            "attached_to_name": doc.name,
                        }
                    )
                    file_doc.insert(ignore_permissions=True)

            gen_response(200, "Quotation created successfully.", doc.name)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for create sales order")
    except Exception as e:
        return exception_handler(e)


def _create_update_quotation(data, quotation_doc, default_warehouse):
    valid_till = data.get("valid_till")
    # total_discount = 0
    for item in data.get("items"):
        item["valid_till"] = valid_till
        item["warehouse"] = default_warehouse
        # if item["discount_amount"]:
        #     total_discount = total_discount + (
        #         float(item["discount_amount"]) * item["qty"]
        #     )
    quotation_doc.update(data)
    # quotation_doc.discount_amount = total_discount
    quotation_doc.apply_discount_on = "Grand Total"
    # quotation_doc.run_method("set_missing_values")
    quotation_doc.run_method("calculate_taxes_and_totals")
    quotation_doc.save()


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
def get_lead_list():
    try:
        lead_list = frappe.get_all("Lead", fields=["name"])
        gen_response(200, "Lead list get successfully", lead_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for lead")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def download_quotation_pdf(id):
    try:
        quotation_doc = frappe.get_doc("Quotation", id)
        default_print_format = (
            frappe.db.get_value(
                "Property Setter",
                dict(property="default_print_format", doc_type=quotation_doc.doctype),
                "value",
            )
            or "Standard"
        )
        download_pdf(
            quotation_doc.doctype,
            quotation_doc.name,
            default_print_format,
            quotation_doc,
        )
    except Exception as e:
        return exception_handler(e)
