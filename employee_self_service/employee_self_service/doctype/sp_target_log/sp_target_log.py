# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SPTargetLog(Document):
    def on_submit(self):
        self.update_employee_target(increment=True)

    def on_cancel(self):
        self.update_employee_target(increment=False)

    def update_employee_target(self, increment=True):
        target_doc = frappe.get_doc("Employee Target Entry", self.employee_target_entry)

        achieved = self.amount if target_doc.metric == "Value" else self.qty
        delta = achieved if increment else -achieved

        if self.item_group:
            for row in target_doc.get("item_group_wise_target"):
                if self.item_group == row.item_group:
                    row.achieved = max(row.achieved + delta, 0)
        else:
            target_doc.achieved = max(target_doc.achieved + delta, 0)

        target_doc.save(ignore_permissions=True)
