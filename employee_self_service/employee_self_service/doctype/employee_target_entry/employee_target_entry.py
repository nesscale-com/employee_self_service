# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_months, get_last_day, cint
from calendar import month_name

# Constants for better maintainability
FREQUENCY_MONTHLY = "Monthly"
FREQUENCY_QUARTERLY = "Quarterly"
FREQUENCY_YEARLY = "Yearly"

STATUS_ACTIVE = "Active"
STATUS_COMPLETE = "Completed"

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
        self._perform_calculations()
        self._validate_team_target_limits()
        self._validate_date_range()
        self._validate_duplicate_employee_item_group()
        
    def before_submit(self):
        self.status = "Active"
        
    def on_submit(self):
        if self.is_group == 1:
            self._create_team_target()
        
    def _create_team_target(self):
        """Create Employee Target Entries based on team or item group targets."""
        
        def calculate_target(row_value, row_type, base_value):
            """Calculate target based on type."""
            if row_type == "Manual":
                return row_value or 0
            elif row_type == "Weightage":
                return (base_value or 0) * (row_value or 0) / 100
            return 0

        # Determine which rows to process
        target_rows = self.item_group_wise_team_targets if self.selector == "Item Group" else self.team_targets

        for row in target_rows:
            target_entry = frappe.new_doc("Employee Target Entry")
            # Common fields
            target_entry.parent_target_entry = self.name
            target_entry.employee = row.employee
            target_entry.target_template = self.target_template
            target_entry.fiscal_year = self.fiscal_year
            target_entry.month = self.month
            target_entry.quarter = self.quarter
            target_entry.start_date = self.start_date
            target_entry.end_date = self.end_date

            if self.selector == "Item Group":
                # Assign item group-wise targets
                for item in target_entry.item_group_wise_target:
                    item.item_group = row.item_group
                    item.target = calculate_target(row.value, row.type, self.team_target)
            else:
                # Assign total target for non-item group
                target_entry.total_target = calculate_target(row.value, row.type, self.team_target)

            target_entry.save(ignore_permissions=True)
            target_entry.submit()
            
    def _validate_required_fields(self):
        """Validate all required fields are properly set."""
        required_fields = {
            'employee': _('Employee'),
            'target_template': _('Target Template'),
            'fiscal_year': _('Fiscal Year')
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

    def _get_cached_fiscal_year(self):
        """Get cached fiscal year document to avoid repeated DB calls."""
        if self._cached_fiscal_year is None and self.fiscal_year:
            try:
                self._cached_fiscal_year = frappe.get_cached_doc("Fiscal Year", self.fiscal_year)
            except frappe.DoesNotExistError:
                frappe.throw(_("Fiscal Year '{0}' does not exist").format(self.fiscal_year))
        return self._cached_fiscal_year
    
    def _get_cached_template(self):
        """Get cached template document to avoid repeated DB calls."""
        if self._cached_template is None and self.target_template:
            try:
                self._cached_template = frappe.get_cached_doc("Employee Target Template", self.target_template)
            except frappe.DoesNotExistError:
                frappe.throw(_("Target Template '{0}' does not exist").format(self.target_template))
        return self._cached_template

    def _perform_calculations(self):
        """Optimize calculation performance with better algorithms."""
        if self.selector == "Item Group":
            self._calculate_item_group_progress()
        else:
            self._calculate_simple_progress()
            
        self._calculate_overall_progress()
        
        # Set status based on progress
        self.status = STATUS_COMPLETE if self.overall_progress >= 100 else STATUS_ACTIVE
    
    def _calculate_item_group_progress(self):
        """Calculate progress for item group based targets."""
        item_group_targets = self.get("item_group_wise_target")
        if not item_group_targets:
            self.total_target = self.total_achieved = self.progress = 0
            self.team_target = self.team_archieved = self.team_progress = 0
            self.overall_progress = 0
            return
        
        # Process all data in a single pass for better performance
        self.total_target = 0
        self.total_achieved = 0
        self.team_target = 0
        self.team_archieved = 0
        total_considered_achieved = 0
        total_considered_team_achieved = 0
        
        for row in item_group_targets:
            personal_target = row.target or 0
            personal_achieved = row.achieved or 0
            considered = min(personal_achieved, personal_target)
            self.total_target += personal_target
            self.total_achieved += personal_achieved
            total_considered_achieved += considered
            row.progress = (considered / personal_target * 100) if personal_target > 0 else 0
            
            team_target = row.team_target or 0
            team_achieved = row.team_achieved or 0
            team_considered = min(team_target, team_achieved)
            self.team_target += team_target
            self.team_achieved += team_achieved
            total_considered_team_achieved += team_considered
            row.team_progress = (team_considered / team_target * 100) if team_target > 0 else 0
            
        self.progress = (total_considered_achieved / self.total_target * 100) if self.total_target > 0 else 0
        self.team_progress = (total_considered_team_achieved / self.team_target * 100) if self.team_target > 0 else 0
    
    def _calculate_simple_progress(self):
        """Calculate progress for simple target entries."""
        self.progress = 0
        if self.total_target and self.total_target > 0:
            considered_achieved = min(self.total_achieved or 0, self.total_target)
            self.progress = (considered_achieved / self.total_target) * 100

        self.team_progress = 0
        if self.team_target and self.team_target > 0:
            considered_team_achieved = min(self.team_achieved or 0, self.team_target)
            self.team_progress = (considered_team_achieved / self.team_target) * 100
            
    def _calculate_overall_progress(self):
        total_weight = (self.total_target or 0) + (self.team_target or 0)
        if total_weight > 0:
            self.overall_progress = (
                (self.progress * (self.total_target or 0) + self.team_progress * (self.team_target or 0))
                / total_weight
            )
        else:
            self.overall_progress = 0
            
    def _validate_team_target_limits(self):
        if not self.is_group == 1:
            return
        
        if self.selector == "Item Group":
            item_group_totals = {
                d.item_group: (d.team_target or 0) for d in (self.item_group_wise_target or [])
            }
            item_group_allocations = frappe._dict()

            for row in self.item_group_wise_team_targets or []:
                if not row.item_group:
                    continue

                if row.type == "Manual":
                    value = row.value or 0
                elif row.type == "Weightage":
                    # Find item_group total target
                    total_target = item_group_totals.get(row.item_group, 0)
                    value = (total_target * (row.value or 0)) / 100
                else:
                    value = 0

                item_group_allocations[row.item_group] = (
                    item_group_allocations.get(row.item_group, 0) + value
                )

            # Validate per item_group
            for ig, allocated in item_group_allocations.items():
                total_allowed = item_group_totals.get(ig, 0)
                if allocated > total_allowed:
                    frappe.throw(
                        f"Total assigned team targets for Item Group <b>{ig}</b> "
                        f"({allocated}) cannot exceed its allowed target ({total_allowed})."
                    )

        else:
            total_team_target = 0
            for row in self.team_targets:
                if row.type == "Manual":
                    total_team_target += row.value or 0
                elif row.type == "Weightage":
                    total_team_target += (self.team_target * (row.value or 0)) / 100

            if total_team_target > (self.team_target or 0):
                frappe.throw(
                    f"Total of Team Targets ({total_team_target}) "
                    f"cannot exceed Total Target ({self.team_target})."
                )

    @frappe.whitelist()
    def get_template_item_groups(self):
        """Fetch child table rows from Employee Target Template doctype."""
        if not self.target_template:
            frappe.msgprint(_("No target template selected"))
            return []
        
        try:
            template_doc = self._get_cached_template()
            return template_doc.get("item_group_list", [])
        except Exception as e:
            frappe.log_error(title="Error fetching template item groups", message=frappe.get_traceback())
            frappe.throw(_("Failed to fetch template data. Please contact administrator."))

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
        except Exception as e:
            frappe.log_error(title="Error calculating date range", message=frappe.get_traceback())
            frappe.throw(_("Error calculating date range. Please check your frequency settings."))

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
            frappe.throw(_("Quarter must be a valid number between 1 and {0}").format(QUARTERS_PER_YEAR))
        
        start_month = (quarter - 1) * MONTHS_PER_QUARTER
        start_date = add_months(fy_start, start_month)
        end_date = get_last_day(add_months(start_date, MONTHS_PER_QUARTER - 1))
        
        return start_date, end_date

    def _validate_date_range(self):
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
        except Exception as e:
            frappe.log_error(title="Error validating date range", message=frappe.get_traceback())
            frappe.throw(_("Unable to validate date range. Please check your settings."))
    
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
        
    def _validate_duplicate_employee_item_group(self):
        """Prevent duplicate (employee + item_group) combinations when selector is 'Item Group'."""
        if self.selector != "Item Group":
            return

        seen = {}
        row_index = 1

        for row in self.item_group_wise_team_targets:
            if not row.employee or not row.item_group:
                row_index += 1
                continue

            key = (row.employee, row.item_group)
            if key in seen:
                frappe.throw(
                    f"Duplicate combination found for Employee <b>{row.employee}</b> "
                    f"and Item Group <b>{row.item_group}</b>.<br>"
                    f"Already exists in Row {seen[key]} and repeated at Row {row_index}."
                )

            seen[key] = row_index
            row_index += 1
        
    @frappe.whitelist()
    def set_sales_person(self):
        if not self.employee:
            return
        
        sales_person = get_sales_person_details(self.employee)
        if sales_person:
            self.sales_person = sales_person.name
            self.is_group = sales_person.is_group
            
def get_sales_person_details(employee, find_child=False):
    """Fetch Sales Person details linked to an employee."""
    sales_person = frappe.db.get_value(
        "Sales Person",
        {"employee": employee, "enabled": 1},
        ["name", "employee", "is_group", "parent_sales_person"],
        as_dict=True,
    )

    if not sales_person:
        return None

    if not find_child:
        return sales_person

    if cint(sales_person.is_group):
        child_sales_person = frappe.get_all(
            "Sales Person",
            {"enabled": 1, "parent_sales_person": sales_person.name},
            ["name", "employee", "is_group", "parent_sales_person"]
        )
        return child_sales_person

    return sales_person

@frappe.whitelist()
def get_team_employee(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe._dict(filters or {})
    employee = filters.get("employee")
    exclude_employees = filters.get("exclude_employees") or []

    if not employee:
        return []

    child_sales_persons = get_sales_person_details(employee, find_child=True)
    if not child_sales_persons:
        return []

    child_employees = [sp.employee for sp in child_sales_persons if sp.get("employee")]
    if not child_employees:
        return []
    
    if exclude_employees:
        child_employees = [e for e in child_employees if e not in exclude_employees]
        if not child_employees:
            return []
    
    employees = frappe.get_all(
        "Employee",
        filters={"name": ["in", child_employees]},
        fields=["name", "employee_name"],
        order_by="employee_name asc"
    )
    return [[emp.name, emp.employee_name] for emp in employees]
    
