import frappe
from frappe import _
from frappe.utils import getdate
from frappe.utils.nestedset import get_descendants_of


def get_employee_from_sales_team(doctype, docname):
    sales_persons = frappe.get_all(
        "Sales Team",
        filters={"parenttype": doctype, "parent": docname},
        fields=["sales_person"],
    )
    employees = []
    for sp in sales_persons:
        emp = frappe.db.get_value("Sales Person", sp.sales_person, "employee")
        if emp:
            employees.append(emp)
    return employees


def get_active_target_entries(employee, target_module, transaction_date):
    """
    Retrieve active Employee Target Entries for specified employee and transaction date.
    
    Filters target entries where the transaction date falls within the configured
    date range and target status is active (In Progress).
    
    Args:
        employee (str): Employee ID
        target_module (str): Document type (Sales Order/Sales Invoice)
        transaction_date (date): Transaction date to validate against target period
        
    Returns:
        list: List of active Employee Target Entry documents
    """
    target_entries = frappe.get_all(
        "Employee Target Entry",
        filters={
            "employee": employee,
            "target_module": target_module,
            "start_date": ["<=", transaction_date],
            "end_date": [">=", transaction_date],
            "status": "In Progress"
        },
        fields=["name"]
    )
    
    active_targets = []
    for target_entry in target_entries:
        target_doc = frappe.get_doc("Employee Target Entry", target_entry.name)
        active_targets.append(target_doc)
    
    return active_targets


def handle_item_group_target(doc, target_doc, employee, metric, transaction_date):
    """
    Process item group-based target tracking for document items.
    
    Evaluates each item in the document against configured target item groups,
    including parent-child hierarchy relationships. Creates individual target
    logs for items that match the target criteria.
    
    Args:
        doc: Sales Order/Sales Invoice document
        target_doc: Employee Target Entry document
        employee (str): Employee ID
        metric (str): Target metric type (Value/Quantity)
        transaction_date (date): Transaction date for the log
    """
    if not hasattr(doc, 'items') or not doc.items:
        return
    
    # Extract target item groups from target configuration
    target_item_groups = []
    for d in target_doc.get("item_group_wise_target", []):
        if d.item_group:
            target_item_groups.append(d.item_group)
    
    if not target_item_groups:
        return
    
    # Include child item groups in target matching
    expanded_item_groups = get_item_group_hierarchy(target_item_groups)
    
    # Process each item against target criteria
    for item in doc.items:
        item_group = item.get("item_group")
        if not item_group:
            # Fallback to item master for item group information
            item_group = frappe.db.get_value("Item", item.item_code, "item_group")
        
        if item_group and item_group in expanded_item_groups:
            create_target_log(
                employee=employee,
                doc=doc,
                target_doc=target_doc,
                metric=metric,
                group_field="item_group",
                group_value=item_group,
                amount=item.amount,
                qty=item.qty,
                transaction_date=transaction_date,
            )


def handle_customer_group_target(doc, target_doc, employee, metric, transaction_date):
    """
    Process customer group-based target tracking for document customer.
    
    Validates if the document's customer belongs to any configured target
    customer groups, including parent-child hierarchy relationships.
    Creates target log when customer group matches target criteria.
    
    Args:
        doc: Sales Order/Sales Invoice document
        target_doc: Employee Target Entry document
        employee (str): Employee ID
        metric (str): Target metric type (Value/Quantity)
        transaction_date (date): Transaction date for the log
    """
    customer_group = doc.get("customer_group")
    if not customer_group:
        # Retrieve customer group from customer master if not in document
        customer_group = frappe.db.get_value("Customer", doc.customer, "customer_group")
    
    if not customer_group:
        return
    
    # Extract target customer groups from target configuration
    target_customer_groups = []
    for d in target_doc.get("customer_group_wise_target", []):
        if d.customer_group:
            target_customer_groups.append(d.customer_group)
    
    if not target_customer_groups:
        return
    
    # Include child customer groups in target matching
    expanded_customer_groups = get_customer_group_hierarchy(target_customer_groups)
    
    if customer_group in expanded_customer_groups:
        create_target_log(
            employee=employee,
            doc=doc,
            target_doc=target_doc,
            metric=metric,
            group_field="customer_group",
            group_value=customer_group,
            amount=doc.total,
            qty=doc.total_qty,
            transaction_date=transaction_date,
        )


def get_item_group_hierarchy(target_groups):
    """
    Expand item groups to include all child groups in the hierarchy using Frappe's built-in functions.
    
    Uses Frappe's nestedset utility to efficiently retrieve all descendant
    groups of the specified target groups, leveraging the optimized nested set model.
    
    Args:
        target_groups (list): List of target item group names
        
    Returns:
        set: Expanded set including target groups and all their children
    """
    expanded_groups = set(target_groups)
    
    # Use Frappe's built-in function to get all descendants for each target group
    for target_group in target_groups:
        try:
            # Get all descendants of the target group
            descendants = get_descendants_of("Item Group", target_group, ignore_permissions=True)
            expanded_groups.update(descendants)
        except Exception:
            # Fallback: if nestedset fails, the target group itself is still included
            pass
    
    return expanded_groups


def get_customer_group_hierarchy(target_groups):
    """
    Expand customer groups to include all child groups in the hierarchy using Frappe's built-in functions.
    
    Uses Frappe's nestedset utility to efficiently retrieve all descendant
    groups of the specified target groups, leveraging the optimized nested set model.
    
    Args:
        target_groups (list): List of target customer group names
        
    Returns:
        set: Expanded set including target groups and all their children
    """
    expanded_groups = set(target_groups)
    
    # Use Frappe's built-in function to get all descendants for each target group
    for target_group in target_groups:
        try:
            # Get all descendants of the target group
            descendants = get_descendants_of("Customer Group", target_group, ignore_permissions=True)
            expanded_groups.update(descendants)
        except Exception:
            # Fallback: if nestedset fails, the target group itself is still included
            pass
    
    return expanded_groups


def handle_combined_target(doc, target_doc, employee, metric, transaction_date):
    """
    Process combined item group and customer group-based target tracking.
    
    Validates both item group and customer group criteria simultaneously.
    Creates target logs only when items match target item groups AND the
    customer belongs to target customer groups, providing dual-layer filtering.
    
    Args:
        doc: Sales Order/Sales Invoice document
        target_doc: Employee Target Entry document
        employee (str): Employee ID
        metric (str): Target metric type (Value/Quantity)
        transaction_date (date): Transaction date for the log
    """
    if not hasattr(doc, 'items') or not doc.items:
        return
    
    # Validate customer group first
    customer_group = doc.get("customer_group")
    if not customer_group:
        customer_group = frappe.db.get_value("Customer", doc.customer, "customer_group")
    
    if not customer_group:
        return
    
    # Extract target customer groups from target configuration
    target_customer_groups = []
    for d in target_doc.get("customer_group_wise_target", []):
        if d.customer_group:
            target_customer_groups.append(d.customer_group)
    
    if not target_customer_groups:
        return
    
    # Check if customer group matches target criteria
    expanded_customer_groups = get_customer_group_hierarchy(target_customer_groups)
    if customer_group not in expanded_customer_groups:
        return  # Customer group doesn't match, skip processing
    
    # Extract target item groups from target configuration
    target_item_groups = []
    for d in target_doc.get("item_group_wise_target", []):
        if d.item_group:
            target_item_groups.append(d.item_group)
    
    if not target_item_groups:
        return
    
    # Include child item groups in target matching
    expanded_item_groups = get_item_group_hierarchy(target_item_groups)
    
    # Process each item against both criteria (item group AND customer group)
    for item in doc.items:
        item_group = item.get("item_group")
        if not item_group:
            item_group = frappe.db.get_value("Item", item.item_code, "item_group")
        
        if item_group and item_group in expanded_item_groups:
            # Both item group and customer group match - create log with both references
            create_target_log(
                employee=employee,
                doc=doc,
                target_doc=target_doc,
                metric=metric,
                group_field="item_group",
                group_value=item_group,
                customer_group_value=customer_group,  # Store customer group as well
                amount=item.amount,
                qty=item.qty,
                transaction_date=transaction_date,
            )


def target_setting():
    """
    Retrieve target management configuration setting.
    
    Returns:
        bool: True if target management is enabled, False otherwise
    """
    return frappe.db.get_single_value("ESS Target Settings", "enable_target_management")


def create_target_log(
    employee,
    doc,
    target_doc,
    metric,
    transaction_date,
    group_field=None,
    group_value=None,
    customer_group_value=None,
    amount=0,
    qty=0,
    ignore_permissions=True,
):
    """
    Create and submit SP Target Log with configurable permission handling.
    
    Generates target achievement records with duplicate prevention and
    comprehensive error handling. Supports both permission-aware and
    permission-ignored creation based on system requirements.
    
    Args:
        employee (str): Employee ID
        doc: Source document (Sales Order/Sales Invoice)
        target_doc: Employee Target Entry document
        metric (str): Target metric type (Value/Quantity)
        transaction_date (date): Transaction date for the log
        group_field (str, optional): Group field name for categorization
        group_value (str, optional): Group value for categorization
        customer_group_value (str, optional): Customer group for combined targeting
        amount (float): Transaction amount
        qty (float): Transaction quantity
        ignore_permissions (bool): Whether to bypass permission checks
    """
    try:
        log_data = {
            "doctype": "SP Target Log",
            "employee": employee,
            "customer": doc.get("customer"),
            "date": frappe.utils.nowdate(),
            "transaction_date": transaction_date,
            "employee_target_entry": target_doc.name,
            "reference_doctype": doc.doctype,
            "reference_docname": doc.name,
            "amount": amount if metric == "Value" else 0,
            "qty": qty if metric == "Quantity" else 0,
        }
        
        if group_field and group_value:
            log_data[group_field] = group_value
        
        # Store customer group for combined targeting scenarios
        if customer_group_value:
            log_data["customer_group"] = customer_group_value

        # Prevent duplicate log creation with enhanced criteria for combined targets
        duplicate_check_filters = {
            "employee": employee,
            "reference_doctype": doc.doctype,
            "reference_docname": doc.name,
            "employee_target_entry": target_doc.name,
        }
        
        if group_field:
            duplicate_check_filters[group_field] = group_value if group_value else ["is", "not set"]
        
        if customer_group_value:
            duplicate_check_filters["customer_group"] = customer_group_value

        existing_log = frappe.db.exists("SP Target Log", duplicate_check_filters)
        
        if existing_log:
            return  # Skip creation if log already exists
        
        target_log = frappe.get_doc(log_data)
        target_log.insert(ignore_permissions=ignore_permissions)
        target_log.flags.ignore_permissions = ignore_permissions
        target_log.submit()
        
    except Exception as e:
        frappe.log_error(
            title="Target Log Creation Failed",
            message=frappe.get_traceback()
        )
