# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

from calendar import month_name

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, cint, get_last_day, getdate

# Constants for better maintainability
FREQUENCY_MONTHLY = "Monthly"
FREQUENCY_QUARTERLY = "Quarterly"
FREQUENCY_YEARLY = "Yearly"

STATUS_IN_PROGRESS = "In Progress"
STATUS_COMPLETE = "Complete"

MONTHS_PER_QUARTER = 3
QUARTERS_PER_YEAR = 4


class EmployeeTargetEntry(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_fiscal_year = None
        self._cached_template = None

    def validate(self):
        self._validate_required_fields()
        self._validate_business_rules()
        self.perform_calculations()
        self.validate_date_range()

    def _validate_required_fields(self):
        """Validate all required fields are properly set."""
        required_fields = {
            "employee": _("Employee"),
            "target_template": _("Target Template"),
            "fiscal_year": _("Fiscal Year"),
        }

        for field, label in required_fields.items():
            if not getattr(self, field, None):
                frappe.throw(_("{0} is required").format(label))

    def _validate_business_rules(self):
        """Validate business-specific rules."""
        # Validate frequency-specific requirements
        if self.frequency == FREQUENCY_MONTHLY and not self.month:
            frappe.throw(_("Month is required when frequency is Monthly"))
        elif self.frequency == FREQUENCY_QUARTERLY and not self.quarter:
            frappe.throw(_("Quarter is required when frequency is Quarterly"))

        # Validate numeric fields
        if (
            hasattr(self, "total_target")
            and self.total_target is not None
            and self.total_target < 0
        ):
            frappe.throw(_("Total Target cannot be negative"))

        if (
            hasattr(self, "total_achieved")
            and self.total_achieved is not None
            and self.total_achieved < 0
        ):
            frappe.throw(_("Total Achieved cannot be negative"))

    def _get_cached_fiscal_year(self):
        """Get cached fiscal year document to avoid repeated DB calls."""
        if self._cached_fiscal_year is None and self.fiscal_year:
            try:
                self._cached_fiscal_year = frappe.get_cached_doc(
                    "Fiscal Year", self.fiscal_year
                )
            except frappe.DoesNotExistError:
                frappe.throw(
                    _("Fiscal Year '{0}' does not exist").format(self.fiscal_year)
                )
        return self._cached_fiscal_year

    def _get_cached_template(self):
        """Get cached template document to avoid repeated DB calls."""
        if self._cached_template is None and self.target_template:
            try:
                self._cached_template = frappe.get_cached_doc(
                    "Employee Target Template", self.target_template
                )
            except frappe.DoesNotExistError:
                frappe.throw(
                    _("Target Template '{0}' does not exist").format(
                        self.target_template
                    )
                )
        return self._cached_template

    def perform_calculations(self):
        """Optimize calculation performance with better algorithms."""
        if self.selector == "Item Group":
            self._calculate_item_group_progress()
        else:
            self._calculate_simple_progress()

        # Set status based on progress
        self.status = STATUS_COMPLETE if self.progress >= 100 else STATUS_IN_PROGRESS

    def _calculate_item_group_progress(self):
        """Calculate progress for item group based targets."""
        item_group_targets = self.get("item_group_wise_target")
        if not item_group_targets:
            self.total_target = self.total_achieved = self.progress = 0
            return

        # Process all data in a single pass for better performance
        self.total_target = 0
        self.total_achieved = 0
        total_considered_achieved = 0

        for row in item_group_targets:
            target = row.target or 0
            achieved = row.achieved or 0
            considered = min(achieved, target)

            self.total_target += target
            self.total_achieved += achieved
            total_considered_achieved += considered
            row.progress = (considered / target * 100) if target > 0 else 0

        self.progress = (
            (total_considered_achieved / self.total_target * 100)
            if self.total_target > 0
            else 0
        )

    def _calculate_simple_progress(self):
        """Calculate progress for simple target entries."""
        if not self.total_target or self.total_target <= 0:
            self.progress = 0
            return

        considered_achieved = min(self.total_achieved or 0, self.total_target)
        self.progress = considered_achieved / self.total_target * 100

    @frappe.whitelist()
    def get_template_item_groups(self):
        """Fetch child table rows from Employee Target Template doctype."""
        if not self.target_template:
            frappe.msgprint(_("No target template selected"))
            return []

        try:
            template_doc = self._get_cached_template()
            return template_doc.get("item_group_list", [])
        except Exception:
            frappe.log_error(
                title="Error fetching template item groups",
                message=frappe.get_traceback(),
            )
            frappe.throw(
                _("Failed to fetch template data. Please contact administrator.")
            )

    @frappe.whitelist()
    def get_date_range(self):
        """Return from_date and to_date based on frequency, fiscal year, month/quarter."""
        if not self.fiscal_year:
            frappe.throw(_("Fiscal Year is required"))

        try:
            fy = self._get_cached_fiscal_year()
        except Exception:
            frappe.throw(_("Invalid Fiscal Year: {0}").format(self.fiscal_year))

        fy_start = getdate(fy.year_start_date)
        fy_end = getdate(fy.year_end_date)

        # Default to fiscal year dates
        start_date, end_date = fy_start, fy_end

        try:
            if self.frequency == FREQUENCY_MONTHLY:
                start_date, end_date = self._get_monthly_date_range(fy_start)
            elif self.frequency == FREQUENCY_QUARTERLY:
                start_date, end_date = self._get_quarterly_date_range(fy_start)
            # For FREQUENCY_YEARLY, we use the default fy_start and fy_end
        except Exception:
            frappe.log_error(
                title="Error calculating date range", message=frappe.get_traceback()
            )
            frappe.throw(
                _("Error calculating date range. Please check your frequency settings.")
            )

        return {"start_date": start_date, "end_date": end_date}

    def _get_monthly_date_range(self, fy_start):
        """Calculate date range for monthly frequency."""
        if not self.month:
            frappe.throw(_("Month is required for Monthly frequency"))

        try:
            selected_month = cint(self.month)
            if not (1 <= selected_month <= 12):
                frappe.throw(_("Invalid month value: {0}").format(selected_month))
        except (ValueError, TypeError):
            frappe.throw(_("Month must be a valid number between 1 and 12"))

        fiscal_start_month = fy_start.month
        offset = (selected_month - fiscal_start_month) % 12
        start_date = add_months(fy_start, offset)
        end_date = get_last_day(start_date)

        return start_date, end_date

    def _get_quarterly_date_range(self, fy_start):
        """Calculate date range for quarterly frequency."""
        if not self.quarter:
            frappe.throw(_("Quarter is required for Quarterly frequency"))

        try:
            quarter = cint(self.quarter)
            if not (1 <= quarter <= QUARTERS_PER_YEAR):
                frappe.throw(_("Invalid quarter value: {0}").format(quarter))
        except (ValueError, TypeError):
            frappe.throw(
                _("Quarter must be a valid number between 1 and {0}").format(
                    QUARTERS_PER_YEAR
                )
            )

        start_month = (quarter - 1) * MONTHS_PER_QUARTER
        start_date = add_months(fy_start, start_month)
        end_date = get_last_day(add_months(start_date, MONTHS_PER_QUARTER - 1))

        return start_date, end_date

    def validate_date_range(self):
        """Validate that start_date and end_date match fiscal year & frequency rules."""
        if not self._are_dates_provided():
            frappe.throw(_("Start Date and End Date are required"))

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date)

        # Validate basic date logic
        if start_date > end_date:
            frappe.throw(_("Start Date cannot be after End Date"))

        # Validate against expected date range
        self._validate_against_expected_range(start_date, end_date)

    def _are_dates_provided(self):
        """Check if both start and end dates are provided."""
        return bool(self.start_date and self.end_date)

    def _validate_against_expected_range(self, start_date, end_date):
        """Validate dates against expected range based on frequency."""
        try:
            date_range = self.get_date_range()
            expected_start = getdate(date_range["start_date"])
            expected_end = getdate(date_range["end_date"])

            period_label = self._get_period_label()

            if not (expected_start <= start_date <= expected_end):
                frappe.throw(
                    _("Start Date must be within {0} ({1} to {2})").format(
                        period_label, expected_start, expected_end
                    )
                )

            if not (expected_start <= end_date <= expected_end):
                frappe.throw(
                    _("End Date must be within {0} ({1} to {2})").format(
                        period_label, expected_start, expected_end
                    )
                )
        except Exception:
            frappe.log_error(
                title="Error validating date range", message=frappe.get_traceback()
            )
            frappe.throw(
                _("Unable to validate date range. Please check your settings.")
            )

    def _get_period_label(self):
        """Generate a human-readable label for the current period."""
        if self.frequency == FREQUENCY_MONTHLY and self.month:
            try:
                month_num = cint(self.month)
                if 1 <= month_num <= 12:
                    return _("{0} {1}").format(month_name[month_num], self.fiscal_year)
            except (ValueError, IndexError):
                pass
            return _("Selected Month {0}").format(self.fiscal_year)
        elif self.frequency == FREQUENCY_QUARTERLY and self.quarter:
            return _("Q{0} {1}").format(self.quarter, self.fiscal_year)
        else:
            return _("Fiscal Year {0}").format(self.fiscal_year)
