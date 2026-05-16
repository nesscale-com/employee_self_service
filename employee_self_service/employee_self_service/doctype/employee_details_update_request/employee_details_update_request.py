# Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeDetailsUpdateRequest(Document):
    def on_submit(self):
        if self.status in ["Pending", "Cancelled"]:
            frappe.throw(
                _("Only Employee Details Update Requests with status 'Approved' or 'Rejected' can be submitted")
            )

        if self.status == "Approved" and not self.is_applied:
            self.apply_to_employee()
            frappe.db.set_value(self.doctype, self.name, "is_applied", 1)

    def before_cancel(self):
        self.status = "Cancelled"

    def on_cancel(self):
        if self.is_applied:
            self.apply_to_employee(reverse=True)
            frappe.db.set_value(self.doctype, self.name, "is_applied", 0)

    def apply_to_employee(self, reverse=False):
        if not self.data:
            return

        data = json.loads(self.data)
        key = "old" if reverse else "new"
        values = data.get(key, {})
        education = values.pop("education", None)

        emp_doc = frappe.get_doc("Employee", self.employee)

        for field, value in values.items():
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