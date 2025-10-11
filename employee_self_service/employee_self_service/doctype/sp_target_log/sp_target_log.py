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
        parent_target_doc = frappe.get_doc("Employee Target Entry", self.parent_target_entry) if self.parent_target_entry else None

        achieved = self.amount if target_doc.metric == "Value" else self.qty
        delta = achieved if increment else -achieved

        if self.item_group:
            updated = False
            for row in target_doc.get("item_group_wise_target"):
                if row.item_group == self.item_group:
                    row.achieved = max(row.achieved + delta, 0)
                    updated = True
            if updated:
                target_doc._perform_calculations()
                target_doc.save(ignore_permissions=True)

            if parent_target_doc:
                updated_team = False
                for row in parent_target_doc.get("item_group_wise_target"):
                    if row.item_group == self.item_group:
                        row.team_achieved = max(row.team_achieved + delta, 0)
                        updated_team = True
                if updated_team:
                    parent_target_doc._perform_calculations()
                    parent_target_doc.save(ignore_permissions=True)

        else:
            target_doc.total_achieved = max(target_doc.total_achieved + delta, 0)
            target_doc._perform_calculations()
            target_doc.save(ignore_permissions=True)

            if parent_target_doc:
                parent_target_doc.team_achieved = max(parent_target_doc.team_achieved + delta, 0)
                parent_target_doc._perform_calculations()
                parent_target_doc.save(ignore_permissions=True)
