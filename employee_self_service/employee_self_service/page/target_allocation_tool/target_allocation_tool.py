import frappe
from frappe.utils import getdate, flt
from frappe import _


@frappe.whitelist()
def get_filtered_targets(employee, from_date, to_date):
    """Get Employee Target Entries filtered by employee and date range."""
    if not employee or not from_date or not to_date:
        return []

    filters = {
        "employee": employee,
        "start_date": ["<=", to_date],
        "end_date": [">=", from_date],
    }

    targets = frappe.get_all(
        "Employee Target Entry",
        filters=filters,
        fields=[
            "name",
            "target_template",
            "start_date",
            "end_date",
            "total_target",
            "total_achieved",
            "status",
            "progress",
        ],
        order_by="creation desc",
    )

    return targets


@frappe.whitelist()
def get_sales_transactions(employee, from_date, to_date, target_entry=None):
    """Get sales orders and invoices for the employee within date range based on target entry."""
    if not employee or not from_date or not to_date or not target_entry:
        frappe.throw(
            _(
                "All parameters are required: Employee, From Date, To Date, and Target Entry"
            )
        )

    # Get sales person from employee
    sales_person = frappe.db.get_value("Sales Person", {"employee": employee}, "name")

    if not sales_person:
        frappe.throw(_("No Sales Person found for Employee {0}").format(employee))

    # Get target entry details to determine which documents to fetch
    target_doc = frappe.get_doc("Employee Target Entry", target_entry)
    target_template = frappe.get_doc(
        "Employee Target Template", target_doc.target_template
    )

    transactions = []

    # Determine which document types to fetch based on target module
    if target_template.target_module == "Sales Order":
        # Fetch only Sales Orders
        transactions = _get_sales_orders(sales_person, from_date, to_date)
    elif target_template.target_module == "Sales Invoice":
        # Fetch only Sales Invoices
        transactions = _get_sales_invoices(sales_person, from_date, to_date)
    else:
        # Default to both if module is not specified or other value
        sales_orders = _get_sales_orders(sales_person, from_date, to_date)
        sales_invoices = _get_sales_invoices(sales_person, from_date, to_date)
        transactions = sales_orders + sales_invoices

    # Check allocation status for each transaction
    for txn in transactions:
        # Check if already allocated
        existing_log = frappe.db.get_value(
            "SP Target Log",
            {
                "reference_docname": txn["name"],
                "reference_doctype": txn["doctype"],
                "docstatus": 1,
            },
            ["name", "employee_target_entry"],
        )

        if existing_log:
            txn["is_allocated"] = True
            txn["allocated_target"] = (
                existing_log[1] if isinstance(existing_log, tuple) else existing_log
            )
            txn["target_log"] = (
                existing_log[0] if isinstance(existing_log, tuple) else existing_log
            )
        else:
            txn["is_allocated"] = False

    return transactions


def _get_sales_orders(sales_person, from_date, to_date):
    """Get sales orders for the sales person."""
    sales_orders = frappe.db.sql(
        """
        SELECT DISTINCT 
            so.name,
            so.customer,
            so.customer_name,
            so.transaction_date,
            so.grand_total,
            'Sales Order' as doctype,
            so.status
        FROM `tabSales Order` so
        INNER JOIN `tabSales Team` st ON st.parent = so.name
        WHERE st.sales_person = %s
        AND so.docstatus = 1
        AND so.transaction_date BETWEEN %s AND %s
        ORDER BY so.transaction_date DESC
    """,
        (sales_person, from_date, to_date),
        as_dict=True,
    )

    return sales_orders


def _get_sales_invoices(sales_person, from_date, to_date):
    """Get sales invoices for the sales person."""
    sales_invoices = frappe.db.sql(
        """
        SELECT DISTINCT 
            si.name,
            si.customer,
            si.customer_name,
            si.posting_date as transaction_date,
            si.grand_total,
            'Sales Invoice' as doctype,
            si.status
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Team` st ON st.parent = si.name
        WHERE st.sales_person = %s
        AND si.docstatus = 1
        AND si.posting_date BETWEEN %s AND %s
        ORDER BY si.posting_date DESC
    """,
        (sales_person, from_date, to_date),
        as_dict=True,
    )

    return sales_invoices


@frappe.whitelist()
def allocate_transaction_to_target(employee, target_entry, doc_type, doc_name):
    """Create SP Target Log entry for the transaction."""

    # Validate inputs
    if not all([employee, target_entry, doc_type, doc_name]):
        frappe.throw(_("All parameters are required"))

    # Check if already allocated
    existing_log = frappe.db.exists(
        "SP Target Log",
        {"reference_docname": doc_name, "reference_doctype": doc_type, "docstatus": 1},
    )

    if existing_log:
        frappe.throw(
            _("{0} {1} is already allocated to a target").format(doc_type, doc_name)
        )

    # Get document details
    doc = frappe.get_doc(doc_type, doc_name)
    target_doc = frappe.get_doc("Employee Target Entry", target_entry)

    # Create SP Target Log
    target_log = frappe.new_doc("SP Target Log")
    target_log.employee = employee
    target_log.employee_target_entry = target_entry
    target_log.customer = doc.customer
    target_log.customer_name = doc.customer_name
    target_log.reference_doctype = doc_type
    target_log.reference_docname = doc_name
    target_log.amount = doc.grand_total
    target_log.transaction_date = (
        doc.transaction_date if doc_type == "Sales Order" else doc.posting_date
    )
    target_log.date = frappe.utils.today()
    target_log.metric = target_doc.metric

    # Get customer group
    customer_group = frappe.db.get_value("Customer", doc.customer, "customer_group")
    if customer_group:
        target_log.customer_group = customer_group

    # Calculate quantity if needed for quantity-based targets
    if target_doc.metric == "Quantity":
        total_qty = (
            frappe.db.sql(
                """
            SELECT SUM(qty) FROM `tab{} Item` WHERE parent = %s
        """.format(
                    doc_type
                ),
                (doc_name,),
            )[0][0]
            or 0
        )
        target_log.qty = total_qty

    # Get item group from first item if needed
    if target_doc.selector == "Item Group":
        item_group = frappe.db.sql(
            """
            SELECT i.item_group FROM `tab{} Item` di
            INNER JOIN `tabItem` i ON i.name = di.item_code
            WHERE di.parent = %s
            LIMIT 1
        """.format(
                doc_type
            ),
            (doc_name,),
        )
        if item_group:
            target_log.item_group = item_group[0][0]

    try:
        target_log.insert()
        target_log.submit()
        return {
            "success": True,
            "message": _("Successfully allocated {0} {1} to target").format(
                doc_type, doc_name
            ),
            "target_log": target_log.name,
        }
    except Exception as e:
        frappe.log_error(f"Error creating SP Target Log: {str(e)}")
        frappe.throw(_("Error allocating transaction: {0}").format(str(e)))


@frappe.whitelist()
def unallocate_transaction(doc_type, doc_name):
    """Cancel SP Target Log entry for the transaction to unallocate it."""

    # Validate inputs
    if not all([doc_type, doc_name]):
        frappe.throw(_("Document Type and Document Name are required"))

    # Find the existing target log
    existing_log = frappe.db.get_value(
        "SP Target Log",
        {"reference_docname": doc_name, "reference_doctype": doc_type, "docstatus": 1},
        ["name", "employee_target_entry"],
    )

    if not existing_log:
        frappe.throw(
            _("{0} {1} is not allocated to any target").format(doc_type, doc_name)
        )

    try:
        # Get the target log document
        target_log_name = (
            existing_log[0] if isinstance(existing_log, tuple) else existing_log
        )
        target_log = frappe.get_doc("SP Target Log", target_log_name)

        # Cancel the target log
        target_log.cancel()

        return {
            "success": True,
            "message": _("Successfully unallocated {0} {1} from target").format(
                doc_type, doc_name
            ),
            "cancelled_log": target_log_name,
        }
    except Exception as e:
        frappe.log_error(f"Error cancelling SP Target Log: {str(e)}")
        frappe.throw(_("Error unallocating transaction: {0}").format(str(e)))


@frappe.whitelist()
def get_employee_list():
    """Get list of employees who have sales person linked."""
    employees = frappe.db.sql(
        """
        SELECT DISTINCT e.name, e.employee_name
        FROM `tabEmployee` e
        INNER JOIN `tabSales Person` sp ON sp.employee = e.name
        WHERE e.status = 'Active'
        ORDER BY e.employee_name
    """,
        as_dict=True,
    )

    return employees
