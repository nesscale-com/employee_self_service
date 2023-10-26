# Copyright (c) 2023, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class PettyExpense(Document):
    def validate(self):
        self.validate_account()

    def validate_account(self):
        default_mode_of_payment_account = frappe.db.get_value(
            "Mode of Payment Account",
            {"parent": self.mode_of_payment, "company": self.company},
            "default_account",
        )
        if not default_mode_of_payment_account:
            frappe.throw(
                _(
                    "Default account not set for mode of payment {0}".format(
                        self.mode_of_payment
                    )
                )
            )
        self.payment_account = default_mode_of_payment_account

    def on_submit(self):
        self.make_journal_entry()

    def on_cancel(self):
        if self.journal_entry:
            if (
                frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
                == 1
            ):
                frappe.throw(
                    _(
                        "{0} is linked with journal entry {1}".format(
                            self.name, self.journal_entry
                        )
                    )
                )

    def make_journal_entry(self):
        jv_doc = frappe.new_doc("Journal Entry")
        jv_doc.entry_type = "Journal Entry"
        jv_doc.company = self.company
        jv_doc.posting_date = self.date
        jv_doc.user_remark = self.description
        jv_doc.append(
            "accounts",
            dict(
                account=self.expense_account,
                debit_in_account_currency=self.amount,
                cost_center=self.cost_center,
            ),
        )
        jv_doc.append(
            "accounts",
            dict(
                account=self.payment_account,
                credit_in_account_currency=self.amount,
                cost_center=self.cost_center,
            ),
        )
        jv_doc = jv_doc.submit()
        self.journal_entry = jv_doc.name
        frappe.db.set_value(self.doctype, self.name, "journal_entry", jv_doc.name)
