# Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document


class EmployeeDetailsUpdateRequest(Document):
    def on_update(self):
        if self.workflow_state != "Approved" or self.is_applied:
            return

        self.apply_to_employee()
        frappe.db.set_value(
            self.doctype,
            self.name,
            "is_applied",
            1,
        )

    def apply_to_employee(self):
        if not self.data:
            return

        data = json.loads(self.data)
        new_values = data.get("new", {})
        education = new_values.pop("education", None)

        emp_doc = frappe.get_doc("Employee", self.employee)

        for field, value in new_values.items():
            if field in emp_doc.meta.get_valid_columns():
                emp_doc.set(field, value or None)

        if education is not None:
            emp_doc.set("education", [])

            for row in education:
                emp_doc.append("education", {
                    "school_univ": row.get("school_univ"),
                    "qualification": row.get("qualification"),
                    "level": row.get("level"),
                    "year_of_passing": row.get("year_of_passing"),
                })
        emp_doc.save()