import json
import frappe
from frappe import _
from frappe.utils import cstr, fmt_money, cint

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
from frappe.model.workflow import get_transitions, apply_workflow

"""order list api for mobile app"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_order_list(start=0, page_length=10, filters=None, list_type="all"):
    try:
        start, page_length = cint(start), cint(page_length)
        filters = filters or {}
        if not isinstance(filters, dict):
            filters = {}
        global_defaults = get_global_defaults()
        currency = global_defaults.get("default_currency")
        status_field = check_workflow_exists("Sales Order") or "status"

        if filters.get("status"):
            filters[status_field] = filters.pop("status")

        # Common fields
        base_fields = [
            "name",
            "customer",
            "customer_name",
            "DATE_FORMAT(transaction_date, '%d-%m-%Y') as transaction_date",
            "grand_total",
            f"{status_field} as status",
            "total_qty",
        ]

        if list_type == "pending":
            filters["custom_is_waiting"] = 1
            raw_orders = frappe.get_list(
                "Sales Order",
                fields=base_fields,
                filters=filters,
                order_by="modified desc",
                limit_page_length=500,
            )

            order_list = []
            for doc in raw_orders:
                so_doc = frappe.get_doc("Sales Order", doc.name)
                if get_transitions(so_doc):
                    doc["is_action_button"] = 1
                    order_list.append(doc)
                if len(order_list) >= (start + page_length):
                    break

            order_list = order_list[start : start + page_length]

        else:
            order_list = frappe.get_list(
                "Sales Order",
                fields=base_fields,
                filters=filters,
                start=start,
                page_length=page_length,
                order_by="modified desc",
            )
            for doc in order_list:
                doc["is_action_button"] = 0

        # Format currency
        for order in order_list:
            order["grand_total"] = fmt_money(order["grand_total"], currency=currency)

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
            "custom_is_waiting",
        ]:
            order_data[response_field] = order_doc.get(response_field)

        user_roles = frappe.get_roles(frappe.session.user)
        bypass_role = frappe.db.get_single_value(
            "Pollenkisan Settings", "order_bypass_role"
        )
        if bypass_role and bypass_role in user_roles:
            order_data["is_release_order"] = 1
        else:
            order_data["is_release_order"] = 0

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
def get_item_list(filters=None, customer=None):
    try:
        if not filters:
            filters = []
        filters.append(["Item", "show_in_mobile", "=", 1])
        item_list = frappe.get_list(
            "Item",
            fields=["name", "item_name", "item_code", "image", "stock_uom"],
            filters=filters,
        )
        items = get_items_rate(item_list, customer=customer)
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
            filters={
                "item_code": item.name,
                "price_list": price_list,
                "uom": item.stock_uom,
            },
            fields=["price_list_rate"],
            order_by="valid_from desc",
        )
        item_price = _get_item_price(
            item_code=item.name,
            price_list=price_list,
            uom=item.stock_uom,
        )
        item_price_currency = fmt_money(
            item_price if item_price else 0.0,
            currency=global_defaults.get("default_currency"),
        )
        item["rate_currency"] = item_price_currency
        item["rate"] = item_price if item_price else 0.0
        item["price_list_rate"] = item_price if item_price else 0.0
        item["price_list_rate_currency"] = item_price_currency
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
        uoms = []
        default_uom_price = _get_item_price(
            item_code=item_doc.get("name"),
            price_list=sales_price_list,
            uom=item_doc.get("stock_uom"),
        )
        for uom_row in item_doc.get("uoms"):
            if uom_row.get("uom") == item_doc.get("stock_uom"):
                uom_hint = f"{uom_row.get('uom')} is default uom"
            else:
                uom_hint = f"1 {uom_row.get('uom')} = {uom_row.get('conversion_factor') } {item_doc.get('stock_uom')}"
            uom_details = dict(
                uom=uom_row.get("uom"),
                conversion_factor=uom_row.get("conversion_factor"),
                uom_hint=uom_hint,
            )
            get_uom_item_price(
                sales_price_list, item, uom_details, default_uom_price, global_defaults
            )
            uoms.append(uom_details)
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
    return frappe.db.get_value(
        "Selling Settings", "Selling Settings", "selling_price_list"
    )


@frappe.whitelist()
def scan_item(barcode):
    try:
        from erpnext.stock.utils import scan_barcode

        item_details = scan_barcode(barcode)
        item_list = frappe.get_list(
            "Item",
            filters={"name": item_details.get("item_code")},
            fields=["name", "item_name", "item_code", "image", "stock_uom"],
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
            _create_update_order(data=data, sales_order_doc=sales_order_doc)
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
                dict(
                    doctype="Sales Order",
                    company=global_defaults.get("default_company"),
                )
            )
            _create_update_order(data=data, sales_order_doc=sales_order_doc)
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


def _create_update_order(data, sales_order_doc):
    default_warehouse = frappe.db.get_single_value(
        "Employee Self Service Settings", "default_warehouse"
    )
    delivery_date = data.get("delivery_date")
    for item in data.get("items"):
        item["delivery_date"] = delivery_date
        item["warehouse"] = default_warehouse
    sales_order_doc.apply_discount_on = "Grand Total"
    sales_order_doc.update(data)
    sales_order_doc.run_method("set_missing_values")
    sales_order_doc.run_method("calculate_taxes_and_totals")
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


@frappe.whitelist()
@ess_validate(methods=["GET"])
def pollen_action_role_list():
    try:
        roles = ["AO", "TO", "ZO", "ZM", "MM", "CEO", "OC", "CMD"]
        return gen_response(
            200, "Waiting Approval Role list fetched successfully", roles
        )
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def pollen_action_role_assignment(order_id, role):
    try:
        apply_workflow_action(order_id, f"AT {role}")
        return gen_response(200, "Role assigned successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def pollen_action_add_comment(order_id, comment, release_order=False):
    try:
        if release_order:
            formatted_comment = generate_comment_html(
                order_id,
                comment,
                title="📌 Sales Order Manually Released",
                style="info",
            )
            apply_workflow_action(
                order_id, "AT Dispatch", formatted_comment, manually_approved=True
            )
            return gen_response(200, "Order manually released successfully")

        formatted_comment = generate_comment_html(
            order_id, comment, title="📤 Sales Order Forwarded", style="success"
        )
        apply_workflow_action(order_id, "Waiting", formatted_comment)
        return gen_response(200, "Comment added successfully")

    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)


def apply_workflow_action(
    order_no, action, formatted_comment=None, manually_approved=False
):
    frappe.flags.ignore_credit_workflow_transition = True
    doc = frappe.get_doc("Sales Order", order_no)
    apply_workflow(doc, action)

    if formatted_comment:
        doc.add_comment(comment_type="Comment", text=formatted_comment)

    if manually_approved:
        doc.db_set("custom_manually_approved", 1)
        doc.db_set("custom_is_waiting", 0)


def generate_comment_html(order_id, comment, title, style="info"):
    # `style` can be "info" or "success" for left border color
    style_color = {"info": "#17a2b8", "success": "#2b8a3e"}.get(  # blue  # green
        style, "#6c757d"
    )  # default gray

    return f"""
        <div style="padding:10px; border-left:4px solid {style_color}; background:#f8f9fa; border-radius:4px;">
            <strong>{title}</strong><br/>
            <b>Sales Order:</b> {order_id}<br/>
            <b>Requested By:</b> {frappe.session.user_fullname} ({frappe.session.user})<br/>
            <b>Comment:</b> {comment}
        </div>
    """
