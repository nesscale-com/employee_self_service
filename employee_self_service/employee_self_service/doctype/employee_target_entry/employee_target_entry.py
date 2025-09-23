# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_months, get_last_day


class EmployeeTargetEntry(Document):
    @frappe.whitelist()
    def get_template_item_groups(self):
        """Fetch child table rows from Employee Target Template doctype."""
        if not self.target_template:
            return []
        template_doc = frappe.get_doc("Employee Target Template", self.target_template)
        return template_doc.get("item_group_list")

    @frappe.whitelist()
    def get_date_range(self):
        """Return from_date and to_date based on frequency, fiscal year, month/quarter."""
        if not self.fiscal_year:
            frappe.throw(_("Fiscal Year is required"))

        fy = frappe.get_doc("Fiscal Year", self.fiscal_year)

        fy_start = getdate(fy.year_start_date)
        fy_end = getdate(fy.year_end_date)

        start_date, end_date = fy_start, fy_end

        if self.frequency == "Monthly":
            if not self.month:
                frappe.throw(_("Month is required for Monthly frequency"))
            month = int(self.month)
            start_date = add_months(fy_start, month - 1)
            end_date = get_last_day(start_date)

        elif self.frequency == "Quarterly":
            if not self.quarter:
                frappe.throw(_("Quarter is required for Quarterly frequency"))
            # Each quarter has 3 months
            quarter = int(self.quarter)
            start_month = (quarter - 1) * 3
            start_date = add_months(fy_start, start_month)
            end_date = get_last_day(add_months(start_date, 2))

        # if frequency == "Yearly" we just return fy_start and fy_end
        return {"start_date": start_date, "end_date": end_date}
