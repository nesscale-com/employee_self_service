import frappe
import json
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    check_workflow_exists,
    get_global_defaults,
    get_attachments,
)
from frappe.utils import fmt_money
from frappe.model.workflow import get_transitions
from frappe.model.workflow import get_workflow_name


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
                    "'0' as 'workflow_active'",
                ],
                order_by="posting_date desc",
                start=start,
                page_length=page_length,
            )
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
                "'1' as 'workflow_active'",
            ],
            order_by="posting_date desc",
        )

        actual_leave_applications = []
        for doc in leave_applications:
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
            filters.extend(
                [
                    ["docstatus", "=", 0],
                    ["status", "=", "Draft"],
                    ["expense_approver", "=", frappe.session.user],
                ]
            )
            fields = [
                "`tabExpense Claim`.name",
                "`tabExpense Claim`.employee",
                "`tabExpense Claim`.employee_name",
                "`tabExpense Claim`.approval_status",
                "`tabExpense Claim`.expense_approver",
                "`tabExpense Claim`.total_claimed_amount",
                "`tabExpense Claim`.posting_date",
                "`tabExpense Claim`.company",
                "`tabExpense Claim Detail`.expense_type",
                "count(`tabExpense Claim Detail`.expense_type) as total_expenses",
            ]

            claims = frappe.get_list(
                "Expense Claim",
                fields=fields,
                filters=filters,
                order_by="`tabExpense Claim`.posting_date desc",
                group_by="`tabExpense Claim`.name",
                start=start,
                page_length=page_length,
            )

            for claim in claims:
                claim["total_claimed_amount"] = fmt_money(
                    claim["total_claimed_amount"],
                    currency=global_defaults.get("default_currency"),
                )

            return gen_response(200, "Team Expense Claim Get Successfully", claims)

        filters.extend([["docstatus", "!=", 2], ["workflow_state", "is", "set"]])

        # Workflow is enabled
        fields = [
            "`tabExpense Claim`.name",
            "`tabExpense Claim`.employee",
            "`tabExpense Claim`.employee_name",
            "`tabExpense Claim`.workflow_state as 'approval_status'",
            "`tabExpense Claim`.expense_approver",
            "`tabExpense Claim`.total_claimed_amount",
            "`tabExpense Claim`.posting_date",
            "`tabExpense Claim`.company",
            "`tabExpense Claim Detail`.expense_type",
            "count(`tabExpense Claim Detail`.expense_type) as total_expenses",
        ]

        claims = frappe.get_list(
            "Expense Claim",
            fields=fields,
            filters=filters,
            order_by="`tabExpense Claim`.posting_date desc",
            group_by="`tabExpense Claim`.name",
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
        return gen_response(200, "Expense detail get successfully.", expense_doc)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Expense")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_status(document, document_no, status):
    try:
        status_field_map = {
            "Leave Application": "status",
            "Expense Claim": "approval_status",
        }
        doc = frappe.get_doc(document, document_no)
        doc.update({f"{status_field_map.get(document)}": status})
        doc.submit()
        return gen_response(200, "Document status updated")
    except Exception as e:
        return exception_handler(e)
