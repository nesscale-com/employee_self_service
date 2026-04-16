import frappe
from frappe import _
from frappe.utils import (
    flt,
    fmt_money,
    getdate,
)

from employee_self_service.mobile.v2.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
    get_date_range,
    get_employee_by_user,
    get_global_defaults,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_transactions(
    date=None,
    from_date=None,
    to_date=None,
    party_type=None,
    party=None,
    download="false",
):
    try:
        if date:
            duration_details = get_date_range(date)
            from_date = getdate(duration_details.get("from_date"))
            to_date = getdate(duration_details.get("to_date"))
        else:
            from_date = getdate(from_date)
            to_date = getdate(to_date)
        if not from_date or not to_date:
            frappe.throw(_("Select First from date and to date"))
        global_defaults = get_global_defaults()
        if not party_type:
            party_type = "Employee"
        if not party:
            emp_data = get_employee_by_user(frappe.session.user)
            party = [emp_data.get("name")]
        allowed_party_types = ["Employee", "Customer", "Supplier"]

        if party_type not in allowed_party_types:
            frappe.throw(
                _("Invalid party type. Allowed party types are {0}").format(
                    ", ".join(allowed_party_types)
                )
            )
        filters_report = {
            "company": global_defaults.get("default_company"),
            "from_date": from_date,
            "to_date": to_date,
            "account": [],
            "party_type": party_type,
            "party": party,
            "group_by": "Group by Party",
            "cost_center": [],
            "project": [],
            "include_dimensions": 1,
        }
        if party_type == "Employee" and isinstance(party, list) and len(party) == 1:
            filters_report["party_name"] = frappe.db.get_value(
                party_type, party[0], "employee_name"
            )
        elif party_type == "Supplier" and isinstance(party, list) and len(party) == 1:
            filters_report["party_name"] = frappe.db.get_value(
                party_type, party[0], "supplier_name"
            )
        else:
            filters_report["party_name"] = (
                ", ".join(party) if party and len(party) > 0 else ""
            )

        from frappe.desk.query_report import run

        res = run("General Ledger", filters=filters_report, ignore_prepared_report=True)
        data = []
        total = {}
        opening_balance = {}
        if res.get("result"):
            for row in res.get("result"):
                if "gl_entry" in row.keys():
                    data.append(
                        {
                            "posting_date": row.get("posting_date").strftime(
                                "%d-%m-%Y"
                            ),
                            "voucher_type": row.get("voucher_type"),
                            "voucher_no": row.get("voucher_no"),
                            "debit": fmt_money(
                                row.get("debit"),
                                currency=global_defaults.get("default_currency"),
                            ),
                            "credit": fmt_money(
                                row.get("credit"),
                                currency=global_defaults.get("default_currency"),
                            ),
                            "balance": fmt_money(
                                row.get("balance"),
                                currency=global_defaults.get("default_currency"),
                            ),
                            "party_type": row.get("party_type"),
                            "party": row.get("party"),
                        }
                    )

                    if flt(row.get("balance")) >= 0:
                        row["color"] = "red"
                    else:
                        row["color"] = "green"
                if "'Opening'" in row.values():
                    opening_balance = {
                        "account": "Opening",
                        "posting_date": from_date.strftime("%d-%m-%Y"),
                        "credit": fmt_money(
                            row.get("credit"),
                            currency=global_defaults.get("default_currency"),
                        ),
                        "debit": fmt_money(
                            row.get("debit"),
                            currency=global_defaults.get("default_currency"),
                        ),
                        "balance": fmt_money(
                            row.get("balance"),
                            currency=global_defaults.get("default_currency"),
                        ),
                    }
                if "'Total'" in row.values():
                    total = {
                        "account": "Total",
                        "posting_date": to_date.strftime("%d-%m-%Y"),
                        "credit": fmt_money(
                            row.get("credit"),
                            currency=global_defaults.get("default_currency"),
                        ),
                        "debit": fmt_money(
                            row.get("debit"),
                            currency=global_defaults.get("default_currency"),
                        ),
                        "balance": fmt_money(
                            row.get("balance"),
                            currency=global_defaults.get("default_currency"),
                        ),
                    }
            data.insert(0, opening_balance)
            data.append(total)

            from frappe.utils.print_format import report_to_pdf

            if download == "true":
                html = frappe.render_template(
                    "employee_self_service/templates/employee_statement.html",
                    {
                        "data": data,
                        "filters": filters_report,
                        "user": frappe.db.get_value(
                            "User", frappe.session.user, "full_name"
                        ),
                    },
                    is_path=True,
                )
                return report_to_pdf(html)
        return gen_response(200, "Ledger Get Successfully", data)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted general ledger report")
    except Exception as e:
        return exception_handler(e)
