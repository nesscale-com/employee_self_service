# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeTarget(Document):
    def validate(self):
        total_target = 0
        total_completed = 0

        for row in self.employee_list:
            total_target += row.target_value or 0
            total_completed += row.completed_value or 0
            row.progress = (
                (row.completed_value / row.target_value * 100)
                if row.target_value
                else 0
            )

        self.overall_progress = (
            (total_completed / total_target * 100) if total_target else 0
        )
