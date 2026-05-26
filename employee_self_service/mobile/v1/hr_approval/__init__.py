import json

import frappe
from frappe.model.workflow import get_transitions, get_workflow_name
from frappe.utils import fmt_money,cint

from employee_self_service.mobile.v1.api_utils import (
    check_workflow_exists,
    ess_validate,
    exception_handler,
    gen_response,
    get_attachments,
    get_employee_by_user,
    get_global_defaults,
)


@frappe.whitelist()
def get_workflow(doctype: str) -> dict:
    workflow = get_workflow_name(doctype)
    if not workflow:
        return frappe._dict()
    return frappe.get_doc("Workflow", workflow)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_team_leave_application(start=0, page_length=20):
    try:
        frappe.log_error(title="Team Leave Application API Called",message="Called")
        workflow = check_workflow_exists("Leave Application")
        emp_data = get_employee_by_user(frappe.session.user)

        filters = [["employee", "!=", emp_data.name]]

        if not workflow:
            filters.extend(
                [
                    ["docstatus", "=", 0],
                    ["status", "=", "Open"],
                    ["leave_approver", "=", frappe.session.user],
                ]
            )
            frappe.log_error(title="filters",message=filters)
            leave_applications = frappe.get_list(
                "Leave Application",
                filters=filters,
                fields=[
                    "employee_name",
                    "name",
                    "posting_date",
                    "from_date",
                    "to_date",
                    "leave_type",
                    "employee",
                    "total_leave_days",
                    "description",
                    "status",
                ],
                order_by="posting_date desc",
                start=start,
                page_length=page_length,
            )
            # Add workflow_active field to each result
            for app in leave_applications:
                app['workflow_active'] = "0"
            return gen_response(
                200, "Leave Application Get Successfully", leave_applications
            )

        filters.extend([["docstatus", "!=", 2], ["workflow_state", "is", "set"]])
        # Workflow is enabled
        leave_applications = frappe.get_list(
            "Leave Application",
            filters=filters,
            fields=[
                "employee_name",
                "name",
                "posting_date",
                "from_date",
                "to_date",
                "leave_type",
                "employee",
                "total_leave_days",
                "description",
                "workflow_state as 'status'",
            ],
            order_by="posting_date desc",
        )

        actual_leave_applications = []
        for doc in leave_applications:
            # Add workflow_active field
            doc['workflow_active'] = "1"
            if doc.get("status"):
                transitions = get_transitions(
                    frappe.get_doc("Leave Application", doc["name"])
                )
                if transitions:
                    actual_leave_applications.append(doc)
                    if len(actual_leave_applications) == page_length:
                        break

        return gen_response(
            200, "Team Leave Application Get Successfully", actual_leave_applications
        )

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_team_expenses(start=0, page_length=20):
    try:
        workflow = check_workflow_exists("Expense Claim")
        emp_data = get_employee_by_user(frappe.session.user)
        global_defaults = get_global_defaults()
        filters = [["employee", "!=", emp_data.name]]

        if not workflow:
            # Use raw SQL for aggregate query with GROUP BY
            claims = frappe.db.sql(
                """
                SELECT 
                    `tabExpense Claim`.name,
                    `tabExpense Claim`.employee,
                    `tabExpense Claim`.employee_name,
                    `tabExpense Claim`.approval_status,
                    `tabExpense Claim`.expense_approver,
                    `tabExpense Claim`.total_claimed_amount,
                    `tabExpense Claim`.posting_date,
                    `tabExpense Claim`.company,
                    `tabExpense Claim Detail`.expense_type,
                    `tabExpense Claim Detail`.name as expense_detail_name,
                    COUNT(`tabExpense Claim Detail`.expense_type) as total_expenses
                FROM `tabExpense Claim`
                LEFT JOIN `tabExpense Claim Detail` ON `tabExpense Claim Detail`.parent = `tabExpense Claim`.name
                WHERE `tabExpense Claim`.employee != %(employee)s
                    AND `tabExpense Claim`.docstatus = 0
                    AND `tabExpense Claim`.status = 'Draft'
                    AND `tabExpense Claim`.expense_approver = %(approver)s
                GROUP BY `tabExpense Claim`.name
                ORDER BY `tabExpense Claim`.posting_date DESC
                LIMIT %(start)s, %(page_length)s
                """,
                {
                    "employee": emp_data.name,
                    "approver": frappe.session.user,
                    "start": start,
                    "page_length": page_length,
                },
                as_dict=True,
            )

            for claim in claims:
                claim["total_claimed_amount"] = fmt_money(
                    claim["total_claimed_amount"],
                    currency=global_defaults.get("default_currency"),
                )

            return gen_response(200, "Team Expense Claim Get Successfully", claims)

        filters.extend([["docstatus", "!=", 2], ["workflow_state", "is", "set"]])

        # Workflow is enabled - use raw SQL for aggregate query with GROUP BY
        claims = frappe.db.sql(
            """
            SELECT 
                `tabExpense Claim`.name,
                `tabExpense Claim`.employee,
                `tabExpense Claim`.employee_name,
                `tabExpense Claim`.workflow_state as approval_status,
                `tabExpense Claim`.expense_approver,
                `tabExpense Claim`.total_claimed_amount,
                `tabExpense Claim`.posting_date,
                `tabExpense Claim`.company,
                `tabExpense Claim Detail`.expense_type,
                `tabExpense Claim Detail`.name as expense_detail_name,
                COUNT(`tabExpense Claim Detail`.expense_type) as total_expenses
            FROM `tabExpense Claim`
            LEFT JOIN `tabExpense Claim Detail` ON `tabExpense Claim Detail`.parent = `tabExpense Claim`.name
            WHERE `tabExpense Claim`.employee != %(employee)s
                AND `tabExpense Claim`.docstatus != 2
                AND `tabExpense Claim`.workflow_state IS NOT NULL
            GROUP BY `tabExpense Claim`.name
            ORDER BY `tabExpense Claim`.posting_date DESC
            """,
            {"employee": emp_data.name},
            as_dict=True,
        )

        updated_expense_claim_list = []
        for doc in claims:
            if doc.get("approval_status"):
                transitions = get_transitions(
                    frappe.get_doc("Expense Claim", doc["name"])
                )
                if transitions:
                    doc["total_claimed_amount"] = fmt_money(
                        doc["total_claimed_amount"],
                        currency=global_defaults.get("default_currency"),
                    )
                    updated_expense_claim_list.append(doc)
                    if len(updated_expense_claim_list) == page_length:
                        break

        return gen_response(
            200, "Team Expense Claim Get Successfully", updated_expense_claim_list
        )
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_team_expense_details(expense_id):
    try:
        if not frappe.has_permission("Expense Claim", "read"):
            raise frappe.PermissionError
        is_workflow = check_workflow_exists("Expense Claim")
        global_defaults = get_global_defaults()
        expense_doc = json.loads(frappe.get_doc("Expense Claim", expense_id).as_json())
        if is_workflow:
            expense_doc["approval_status"] = expense_doc.get("workflow_state")
            expense_doc["workflow_active"] = "1"
        else:
            expense_doc["workflow_active"] = "0"
        expense_doc["attachments"] = get_attachments("Expense Claim", expense_id)
        for row in expense_doc.get("expenses"):
            row["amount"] = fmt_money(
                row.get("amount"), currency=global_defaults.get("default_currency")
            )
        expense_doc["total_claimed_amount"] = fmt_money(
            expense_doc["total_claimed_amount"],
            currency=global_defaults.get("default_currency"),
        )
        expense_doc["currency_symbol"] = frappe.db.get_value(
            "Currency", global_defaults.get("default_currency"), "symbol"
        )
        return gen_response(200, "Expense detail get successfully.", expense_doc)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Expense")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_status(document, document_no, status, expenses=None):
    try:
        status_field_map = {
            "Leave Application": "status",
            "Expense Claim": "approval_status",
        }
        status_field = status_field_map.get(document)

        if not status_field:
            return gen_response(400, f"Unsupported document type: {document}")

        doc = frappe.get_doc(document, document_no)

        if not doc.has_permlevel_access_to(status_field, permission_type="write"):
            field_label = status_field.replace("_", " ").title()
            return gen_response(
                403,
                f"You do not have permission to update the '{field_label}' field in this {document}.",
            )

        doc.set(status_field, status)

        if document == "Expense Claim" and expenses:
            for expense in expenses:
                for row in doc.expenses:
                    if row.get("name") == expense.get("name"):
                        row.sanctioned_amount = expense.get("sanctioned_amount")

        doc.submit()

        return gen_response(
            200, f"{document} '{document_no}' status updated to '{status}'."
        )

    except frappe.PermissionError:
        return gen_response(
            403,
            f"You are not permitted to perform this action on {document} '{document_no}'.",
        )

    except frappe.DoesNotExistError:
        return gen_response(404, f"{document} '{document_no}' not found.")

    except Exception as e:
        return exception_handler(e)
