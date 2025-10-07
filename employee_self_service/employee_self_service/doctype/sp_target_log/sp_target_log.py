# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SPTargetLog(Document):
    def validate(self):
        if not self.transaction_date:
            if self.reference_doctype == "Sales Order":
                self.transaction_date = frappe.db.get_value("Sales Order", self.reference_docname, "transaction_date")
            elif self.reference_doctype == "Sales Invoice":
                self.transaction_date = frappe.db.get_value("Sales Invoice", self.reference_docname, "posting_date")
            else:
                self.transaction_date = frappe.utils.nowdate()

    def on_submit(self):
        self.update_employee_target(increment=True)

    def on_cancel(self):
        self.update_employee_target(increment=False)

    def update_employee_target(self, increment=True):
        target_doc = frappe.get_doc("Employee Target Entry", self.employee_target_entry)

        achieved = self.amount if target_doc.metric == "Value" else self.qty
        delta = achieved if increment else -achieved

        # target update item group wise
        if self.item_group:
            for row in target_doc.get("item_group_wise_target"):
                parent = frappe.db.get_value(
                    "Item Group", self.item_group, "parent_item_group"
                )
                if parent:
                    if parent == row.item_group:
                        row.achieved = max(row.achieved + delta, 0)
                    elif self.item_group == row.item_group:
                        row.achieved = max(row.achieved + delta, 0)

        # target update customer group wise
        elif self.customer_group:
            for row in target_doc.get("customer_group_wise_target"):
                parent = frappe.db.get_value(
                    "Customer Group", self.customer_group, "parent_customer_group"
                )
                if parent:
                    if parent == row.customer_group:
                        row.achieved = max(row.achieved + delta, 0)
                    elif self.customer_group == row.customer_group:
                        row.achieved = max(row.achieved + delta, 0)
        else:
            target_doc.total_achieved = max(target_doc.total_achieved + delta, 0)

        target_doc.save(ignore_permissions=True)
