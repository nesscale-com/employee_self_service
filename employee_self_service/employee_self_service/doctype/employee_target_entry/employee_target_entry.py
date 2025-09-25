# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_months, get_last_day
from calendar import month_name


class EmployeeTargetEntry(Document):
    def validate(self):
        self.perform_calculations()
        self.validate_date_range()

    def perform_calculations(self):
        self.total_achieved = 0
        self.total_target = 0

        if self.selector == "Item Group":
            total_considered_achieved = 0
            for row in self.get("item_group_wise_target"):
                self.total_target += row.target
                self.total_achieved += row.achieved
                total_considered_achieved += min(row.achieved, row.target)

            self.progress = (
                (total_considered_achieved / self.total_target * 100)
                if self.total_target
                else 0
            )

            for row in self.get("item_group_wise_target"):
                row.progress = (
                    (min(row.achieved, row.target) / row.target * 100)
                    if row.target
                    else 0
                )
        else:
            self.progress = (
                (min(self.achieved, self.target) / self.target * 100)
                if self.target
                else 0
            )

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
            selected_month = int(self.month)
            fiscal_start_month = fy_start.month
            offset = (selected_month - fiscal_start_month) % 12
            start_date = add_months(fy_start, offset)
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

    def validate_date_range(self):
        """Validate that start_date and end_date match fiscal year & frequency rules."""

        if not self.start_date or not self.end_date:
            frappe.throw(_("Start Date and End Date are required"))

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date)

        date_range = self.get_date_range()
        expected_start = getdate(date_range["start_date"])
        expected_end = getdate(date_range["end_date"])

        if self.frequency == "Monthly" and self.month:
            label = _("{0} {1}").format(month_name[int(self.month)], self.fiscal_year)
        elif self.frequency == "Quarterly" and self.quarter:
            label = _("Q{0} {1}").format(self.quarter, self.fiscal_year)
        else:
            label = _("Fiscal Year {0}").format(self.fiscal_year)

        if not (expected_start <= start_date <= expected_end):
            frappe.throw(
                _("Start Date must be within {0} ({1} to {2})").format(
                    label, expected_start, expected_end
                )
            )

        if not (expected_start <= end_date <= expected_end):
            frappe.throw(
                _("End Date must be within {0} ({1} to {2})").format(
                    label, expected_start, expected_end
                )
            )

        if start_date > end_date:
            frappe.throw(_("Start Date cannot be after End Date"))
