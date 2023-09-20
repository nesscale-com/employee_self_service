import frappe
from frappe import _
from frappe.utils import today, flt
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    prepare_json_data,
    exception_handler,
    get_actions,
    check_workflow_exists,
)


"""payment entry meta data"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_payment_entry_data():
    try:
        payment_entry_meta = frappe.get_meta("Payment Entry")
        meta_data = {}
        meta_data["naming_series"] = payment_entry_meta.get_field(
            "naming_series"
        ).options.split("\n")
        meta_data["payment_type"] = payment_entry_meta.get_field(
            "payment_type"
        ).options.split("\n")
        meta_data["mode_of_payment"] = frappe.get_list("Mode of Payment", pluck="name")
        meta_data["company"] = frappe.get_list("Company", pluck="name")
        meta_data["party_type"] = frappe.get_list(
            "Party Type", pluck="name", order_by="name asc"
        )
        meta_data["defaults"] = get_defaults_for_pe(payment_entry_meta)
        meta_data["workflow"] = (
            True if check_workflow_exists("Payment Entry") else False
        )

        gen_response(200, "Payment Entry meta data get successfully", meta_data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Payment Entry")
    except Exception as e:
        return exception_handler(e)


def get_defaults_for_pe(payment_entry_meta):
    naming_series = payment_entry_meta.get_field("naming_series")
    return dict(
        company=frappe.defaults.get_global_default("company"),
        naming_series=naming_series.default or naming_series.options.split("\n")[0],
    )


"""get party by party type"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_party(party_type):
    try:
        if party_type == "Customer":
            meta_data = frappe.get_list(
                party_type, fields=["name", "customer_name as party_name"]
            )
        if party_type == "Employee":
            meta_data = frappe.get_list(
                party_type, fields=["name", "employee_name as party_name"]
            )
        if party_type == "Shareholder":
            meta_data = frappe.get_list(
                party_type, fields=["name", "title as party_name"]
            )
        if party_type == "Supplier":
            meta_data = frappe.get_list(
                party_type, fields=["name", "supplier_name as party_name"]
            )
        gen_response(200, "data get successfully", meta_data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted")
    except Exception as e:
        return exception_handler(e)


"""for getting party balance and account details"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_party_details(party_type, party, company):
    try:
        from erpnext.accounts.doctype.payment_entry.payment_entry import (
            get_party_details,
        )

        party_details = get_party_details(
            company=company, party_type=party_type, party=party, date=today()
        )

        gen_response(200, "Party details get successfully", party_details)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Party")
    except Exception as e:
        return exception_handler(e)


"""
Get list of accounts for paid_from field
Account list will be based on payment type
"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_account_paid_from_list(party_type, payment_type, company):
    try:
        if payment_type == "Receive":
            if party_type in ["Employee", "Shareholder", "Supplier"]:
                account_type = ["Payable"]
            if party_type == "Customer":
                account_type = ["Receivable"]

        if payment_type == "Pay" or payment_type == "Internal Transfer":
            account_type = ["Bank", "Cash"]

        accounts = frappe.get_list(
            "Account",
            pluck="name",
            filters={
                "account_type": ["in", account_type],
                "is_group": 0,
                "company": company,
            },
        )
        gen_response(200, "Account list get successfully", accounts)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Account list")
    except Exception as e:
        return exception_handler(e)


"""
Get list of accounts for paid_to field
Account list will be based on payment type
"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_account_paid_to_list(party_type, payment_type, company):
    try:
        if payment_type == "Receive" or payment_type == "Internal Transfer":
            account_type = ["Bank", "Cash"]

        if payment_type == "Pay":
            if party_type in ["Employee", "Shareholder", "Supplier"]:
                account_type = ["Payable"]
            if party_type == "Customer":
                account_type = ["Receivable"]

        accounts = frappe.get_list(
            "Account",
            pluck="name",
            filters={
                "account_type": ["in", account_type],
                "is_group": 0,
                "company": company,
            },
        )

        gen_response(200, "Account list get successfully", accounts)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Account list")
    except Exception as e:
        return exception_handler(e)


"""
Get all transactions for selected party
"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_invoice_list(party_type, party, account, paid_amount=0):
    try:
        from erpnext.accounts.utils import get_outstanding_invoices

        outstanding_invoice = get_outstanding_invoices(
            party_type=party_type, party=party, account=account
        )
        paid_amount = flt(paid_amount)
        for reference in outstanding_invoice:
            reference["reference_doctype"] = reference["voucher_type"]
            reference["reference_name"] = reference["voucher_no"]
            reference["total_amount"] = reference["invoice_amount"]
            if paid_amount > flt(reference["outstanding_amount"]):
                reference["allocated_amount"] = flt(reference["outstanding_amount"])
                paid_amount = paid_amount - reference["allocated_amount"]
            else:
                reference["allocated_amount"] = paid_amount
                if paid_amount > 0:
                    paid_amount = paid_amount - reference["allocated_amount"]
            del (
                reference["voucher_type"],
                reference["voucher_no"],
                reference["invoice_amount"],
                reference["posting_date"],
                reference["payment_amount"],
                reference["currency"],
            )
        gen_response(200, "Invoice list get successfully", outstanding_invoice)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Account list")
    except Exception as e:
        return exception_handler(e)


"""
Make payment api
"""


@frappe.whitelist()
@ess_validate(methods=["POST"])
def make_payment(*args, **kwargs):
    try:
        data = kwargs
        if data.get("name"):
            payment_entry_doc = frappe.get_doc("Payment Entry", data.get("name"))
            if not check_workflow_exists("Payment Entry"):
                is_submit = data.get("submit")
                del data["submit"]
                payment_entry_doc.update(data)
                if is_submit == True:
                    payment_entry_doc.submit()
                else:
                    payment_entry_doc.save()
            else:
                payment_entry_doc.save()
            return gen_response(200, "Payment entry updated successfully")

        payment_doc = frappe.get_doc(
            dict(
                doctype="Payment Entry",
                naming_series=data.get("naming_series"),
                payment_type=data.get("payment_type"),
                posting_date=data.get("posting_date"),
                mode_of_payment=data.get("mode_of_payment"),
                company=data.get("company"),
                party_type=data.get("party_type"),
                party=data.get("party"),
                paid_from=data.get("paid_from"),
                paid_to=data.get("paid_to"),
                paid_amount=data.get("paid_amount"),
                reference_no=data.get("reference_no"),
                reference_date=data.get("reference_date"),
                received_amount=data.get("paid_amount"),
                references=data.get("references"),
            )
        )
        if not check_workflow_exists("Payment Entry"):
            if data.get("submit") == True:
                payment_doc.submit()
            else:
                payment_doc.insert()
        else:
            payment_doc.save()
        if data.get("attachments") is not None:
            for file in data.get("attachments"):
                file_doc = frappe.get_doc(
                    dict(
                        doctype="File",
                        file_url=file.get("file_url"),
                        attached_to_doctype="Payment Entry",
                        attached_to_name=payment_doc.name,
                    )
                ).insert(ignore_permissions=True)
        return gen_response(200, "Payment added successfully")
    except Exception as e:
        return exception_handler(e)


"""get all payment entries list"""


@frappe.whitelist()
@ess_validate(methods=["POST"])
def get_payment_entry_list(start=0, page_length=10, filters=None):
    try:
        status_field = check_workflow_exists("Payment Entry")
        if not status_field:
            status_field = "status"
        if filters.get("status"):
            status_val = filters.get("status")
            del filters["status"]
            filters[status_field] = status_val
        payment_entry_list = frappe.get_list(
            "Payment Entry",
            fields=[
                "name",
                "posting_date",
                "mode_of_payment",
                "party",
                "party_name",
                "paid_amount",
                "payment_type",
                f"{status_field} as status",
            ],
            start=start,
            page_length=page_length,
            order_by="modified desc",
            filters=filters,
        )

        gen_response(200, "Payment Entry list get successfully", payment_entry_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for Payment Entry")
    except Exception as e:
        return exception_handler(e)


"""get payment entry data by payment id"""


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_payment_entry(id):
    try:
        if not id:
            return gen_response(500, "Payment Entry id is required")
        if not frappe.db.exists("Payment Entry", id):
            return gen_response(500, "Payment entry does not exists")
        payment_entry = frappe.get_doc("Payment Entry", id).as_dict()

        payment_entry_doc = prepare_json_data(
            [
                "name",
                "payment_type",
                "posting_date",
                "mode_of_payment",
                "company",
                "party_type",
                "party",
                "party_name",
                "paid_from",
                "paid_to",
                "paid_amount",
                "reference_no",
                "reference_date",
                "workflow_state",
            ],
            payment_entry,
        )
        reference_list = []
        for reference in payment_entry.get("references"):
            reference_list.append(
                prepare_json_data(
                    [
                        "outstanding_amount",
                        "due_date",
                        "reference_doctype",
                        "reference_name",
                        "total_amount",
                        "allocated_amount",
                    ],
                    reference,
                )
            )
        payment_entry_doc["next_action"] = get_actions(payment_entry, payment_entry_doc)
        payment_entry_doc["allow_edit"] = (
            True if payment_entry.get("docstatus") == 0 else False
        )
        payment_entry_doc["references"] = reference_list
        payment_entry_doc["attachments"] = get_payment_entry_attachments(id)
        return gen_response(200, "Payment Entry get successfully", payment_entry_doc)
    except Exception as e:
        return exception_handler(e)


def get_payment_entry_attachments(id):
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Payment Entry", "attached_to_name": id},
        fields=["*"],
    )


@frappe.whitelist()
@ess_validate(methods=["DELETE"])
def delete_payment_entry(id):
    try:
        if not id:
            return gen_response(500, "Payment entry id is required")
        if not frappe.db.exists("Payment Entry", id):
            return gen_response(500, "Payment entry does not exists")

        payment_doc = frappe.get_doc("Payment Entry", id)
        if payment_doc.docstatus == 1:
            payment_doc.flags.ignore_permissions = True
            payment_doc.cancel()
        frappe.delete_doc(
            "Payment Entry",
            id,
        )
        return gen_response(200, "Payment entry deleted successfully")
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)


@frappe.whitelist()
def get_status_list(doctype):
    try:
        status_list = []
        workflow_name = frappe.get_all(
            "Workflow",
            filters={"document_type": doctype, "is_active": 1},
            fields=["name"],
        )
        if workflow_name:
            workflow_states = frappe.get_all(
                "Workflow Document State",
                filters=[["parent", "=", workflow_name]],
                fields=["*"],
            )
            for workflow_state in workflow_states:
                status_list.append(workflow_state.state)
        else:
            payment_entry_meta = frappe.get_meta("Payment Entry")
            status_list = payment_entry_meta.get_field("status").options.split("\n")
        return gen_response(200, "document status get successfully", status_list)
    except Exception as e:
        frappe.db.rollback()
        return exception_handler(e)
