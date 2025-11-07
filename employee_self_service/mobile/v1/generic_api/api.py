"""
Generic CRUD APIs for any DocType
Simple and straightforward implementation

This module provides 4 generic APIs that work with any Frappe DocType:
1. get_list - Get paginated list of documents with optional aggregation
2. get_details - Get complete document details
3. create - Create new document or update existing (if name provided)
4. update - Update existing document by name

Features:
- Works with any DocType without custom code
- Auto-discovers list fields from DocType meta
- Supports child table aggregation (count, sum)
- Handles save and submit actions
- Proper error handling and logging

Usage:
    All APIs are whitelisted and can be called via:
    /api/method/employee_self_service.mobile.v1.generic_api.api.<function_name>
"""

import frappe
from frappe import _
from frappe.utils import cint
from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
    get_employee_by_user,
)


def get_list_fields_from_meta(doctype):
    """Get list fields from doctype meta"""
    meta = frappe.get_meta(doctype)
    fields = ["name"]

    # Get fields marked for list view
    for field in meta.fields:
        if field.in_list_view and field.fieldtype not in [
            "Section Break",
            "Column Break",
            "Tab Break",
            "HTML",
        ]:
            fields.append(field.fieldname)

    # If no list view fields, add common fields
    if len(fields) == 1:
        common_fields = ["status", "title", "subject", "modified"]
        for field_name in common_fields:
            if meta.has_field(field_name):
                fields.append(field_name)

    return fields


@frappe.whitelist()
def get_list(
    doctype,
    fields=[],
    filters=[],
    start=0,
    page_length=20,
    order_by=None,
    aggregate=None,
    **kwargs,
):
    """
    Generic API to get list of documents for any doctype

    Args:
        doctype (str): DocType name (required)
        fields (list): List of field names to fetch (optional, defaults to list view fields from meta)
        filters (list/dict): Filters to apply (optional)
        start (int): Pagination start position (default: 0)
        page_length (int): Number of records per page (default: 20)
        order_by (str): Sort order (default: "modified desc")
        aggregate (list): List of aggregation configurations (optional)
                         Each config should have:
                         - table_name: Child table DocType name (e.g., "Purchase Order Item")
                         - function: Aggregation function ("count" or "sum")
                         - field_name: Field to aggregate (required for "sum", empty for "count")
        **kwargs: Additional keyword arguments (not used currently)

    Examples:
        Simple list:
        GET /api/method/employee_self_service.mobile.v1.generic_api.api.get_list?doctype=Purchase Order

        With filters:
        POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_list
        Body: {
            "doctype": "Purchase Order",
            "filters": [["status", "=", "Draft"]]
        }

        With aggregation:
        POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_list
        Body: {
            "doctype": "Purchase Order",
            "aggregate": [
                {"table_name": "Purchase Order Item", "function": "count", "field_name": ""},
                {"table_name": "Purchase Order Item", "function": "sum", "field_name": "qty"}
            ]
        }

    Returns:
        dict: Response with status code, message, and data containing:
            - items: List of documents with requested fields
            - items_count: Count of child table items (if aggregate count requested)
            - total_{field_name}: Sum of field (if aggregate sum requested)
    """
    try:
        # Parse fields
        if not fields:
            fields = get_list_fields_from_meta(doctype)

        # Build filters
        if not filters:
            filters = []

        # Get documents
        documents = frappe.get_list(
            doctype,
            filters=filters,
            fields=fields,
            start=cint(start),
            page_length=cint(page_length),
            order_by=order_by or "modified desc",
        )

        # Add aggregation only if requested
        # Aggregation allows counting child table items or summing fields
        if aggregate and documents:
            try:
                import json

                # Parse aggregate parameter
                # Supports both JSON string (from GET) and list (from POST body)
                # Format: [{"table_name":"Purchase Order Item","function":"count","field_name":""},
                #          {"table_name":"Purchase Order Item","function":"sum","field_name":"qty"}]

                if isinstance(aggregate, str):
                    # From GET query parameter - parse JSON string
                    aggregate_list = json.loads(aggregate)
                elif isinstance(aggregate, list):
                    # From POST body - already parsed by Frappe
                    aggregate_list = aggregate
                else:
                    aggregate_list = []

                # Process each aggregation configuration
                for agg_config in aggregate_list:
                    table_name = agg_config.get("table_name")
                    function = agg_config.get("function", "").lower()
                    field_name = agg_config.get("field_name", "")

                    # Skip invalid configurations
                    if not table_name or not function:
                        continue

                    # Apply aggregation to each document in the list
                    for doc in documents:
                        if function == "count":
                            # Count child table items using direct SQL for best performance
                            count = frappe.db.count(
                                table_name,
                                filters={
                                    "parent": doc.get("name"),
                                    "parenttype": doctype,
                                },
                            )
                            doc["items_count"] = count

                        elif function == "sum" and field_name:
                            # Sum a specific field in child table using SQL
                            result = frappe.db.sql(
                                f"""
                                SELECT SUM(`{field_name}`) as total
                                FROM `tab{table_name}`
                                WHERE parent = %s AND parenttype = %s
                                """,
                                (doc.get("name"), doctype),
                                as_dict=True,
                            )
                            doc[f"total_{field_name}"] = result[0].get("total") or 0

            except Exception as agg_error:
                # Log aggregation errors but don't fail the entire request
                frappe.log_error(
                    title="Generic API - Aggregation error",
                    message=f"Error in aggregation: {str(agg_error)}\n{frappe.get_traceback()}",
                )
                # Continue without aggregation data

        return gen_response(200, "List Details Get Successfully", documents)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def get_details(doctype, name):
    """
    Generic API to get complete document details for any doctype
    Returns the full document object with all fields including child tables

    Args:
        doctype (str): DocType name (required)
        name (str): Document name/ID (required)

    Examples:
        GET /api/method/employee_self_service.mobile.v1.generic_api.api.get_details?doctype=Purchase Order&name=PO-001

        POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_details
        Body: {
            "doctype": "Purchase Order",
            "name": "PO-001"
        }

    Returns:
        dict: Response with status code, message, and data containing the complete document object
              including all fields, child tables, and computed values
    """
    try:
        if not name:
            frappe.throw(_("Document name is required"))

        # Check if document exists
        if not frappe.db.exists(doctype, name):
            frappe.throw(_("{0} {1} not found").format(doctype, name))

        # Get document
        doc = frappe.get_doc(doctype, name)
        return gen_response(200, "Document Details Get Successfully", doc)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def create(doctype, save_action="save", **data):
    """
    Generic API to create or update a document for any doctype
    If 'name' is provided in data, updates existing document; otherwise creates new one

    Args:
        doctype (str): DocType name (required)
        save_action (str): Action to perform - "save" or "submit" (default: "save")
        **data: Document field values including child table data

    Examples:
        Create new document:
        POST /api/method/employee_self_service.mobile.v1.generic_api.api.create
        Body: {
            "doctype": "Purchase Order",
            "supplier": "SUP-001",
            "schedule_date": "2025-12-01",
            "items": [
                {"item_code": "ITEM-001", "qty": 10, "rate": 100}
            ],
            "save_action": "save"
        }

        Update existing document:
        POST /api/method/employee_self_service.mobile.v1.generic_api.api.create
        Body: {
            "doctype": "Purchase Order",
            "name": "PO-001",
            "supplier": "SUP-002",
            "save_action": "submit"
        }

    Returns:
        dict: Response with status code, message, and data containing:
            - name: Document name/ID
            - docstatus: Document status (0=Draft, 1=Submitted, 2=Cancelled)
    """
    try:
        # Check if updating existing document or creating new
        if data.get("name"):
            doc = frappe.get_doc(doctype, data.get("name"))
        else:
            doc = frappe.new_doc(doctype)

        # Update document with data
        doc.update(data)

        # Save or submit based on save_action
        if save_action == "submit" and doc.meta.is_submittable:
            doc.submit()
        else:
            doc.save()

        return gen_response(
            200,
            f"{doctype} has been {'submitted' if save_action == 'submit' else 'saved'} successfully",
            {"name": doc.name, "docstatus": doc.docstatus},
        )

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to perform this action")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def update(doctype, name, save_action="save", **data):
    """
    Generic API to update an existing document for any doctype
    Only works on draft documents (docstatus=0)

    Args:
        doctype (str): DocType name (required)
        name (str): Document name/ID to update (required)
        save_action (str): Action to perform - "save" or "submit" (default: "save")
        **data: Document field values to update (can include child table data)

    Examples:
        Update and save:
        POST /api/method/employee_self_service.mobile.v1.generic_api.api.update
        Body: {
            "doctype": "Purchase Order",
            "name": "PO-001",
            "supplier": "SUP-002",
            "remarks": "Updated supplier",
            "save_action": "save"
        }

        Update and submit:
        POST /api/method/employee_self_service.mobile.v1.generic_api.api.update
        Body: {
            "doctype": "Purchase Order",
            "name": "PO-001",
            "status": "Approved",
            "save_action": "submit"
        }

    Returns:
        dict: Response with status code, message, and data containing:
            - name: Document name/ID
            - docstatus: Document status (0=Draft, 1=Submitted, 2=Cancelled)

    Notes:
        - Cannot update submitted (docstatus=1) or cancelled (docstatus=2) documents
        - Submit action only works if document is draft (docstatus=0) and submittable
    """
    try:
        if not name:
            return gen_response(500, "Document name is required")

        # Check if document exists
        if not frappe.db.exists(doctype, name):
            return gen_response(500, f"{doctype} {name} not found")

        # Get document
        doc = frappe.get_doc(doctype, name)

        # Check if document can be modified
        if doc.docstatus == 2:
            return gen_response(500, "Cannot modify cancelled document")

        if doc.docstatus == 1:
            return gen_response(500, "Cannot modify submitted document")

        # Update document
        doc.update(data)

        # Save or submit based on save_action
        if save_action == "submit" and doc.meta.is_submittable and doc.docstatus == 0:
            doc.submit()
        else:
            doc.save()

        return gen_response(
            200,
            f"{doctype} has been {'submitted' if save_action == 'submit' else 'updated'} successfully",
            {"name": doc.name, "docstatus": doc.docstatus},
        )

    except frappe.PermissionError:
        return gen_response(500, "Not permitted to perform this action")
    except Exception as e:
        return exception_handler(e)
