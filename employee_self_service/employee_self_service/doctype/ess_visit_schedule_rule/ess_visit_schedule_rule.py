# Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class ESSVisitScheduleRule(Document):
	def validate(self):
		self.validate_schedule_config()
		self.validate_based_on()
		self.validate_date_of_month()
		
	def validate_schedule_config(self):
		if self.schedule_type == "Daily":
			days_selected = any([
				self.monday, self.tuesday, self.wednesday, self.thursday,
				self.friday, self.saturday, self.sunday
			])
			if not days_selected:
				frappe.throw(_("Please select at least one day for Daily schedule"))
				
		elif self.schedule_type in ["Weekly", "Fortnightly"]:
			if not self.day_of_week:
				frappe.throw(_("Please select a day for {0} schedule").format(self.schedule_type))
				
		elif self.schedule_type == "Monthly":
			if not self.date_of_month:
				frappe.throw(_("Please select date of month for Monthly schedule"))
				
		elif self.schedule_type == "Quarterly":
			if not self.quarter:
				frappe.throw(_("Please select a quarter for Quarterly schedule"))
			if not self.date_of_month:
				frappe.throw(_("Please select date of month for Quarterly schedule"))
				
		elif self.schedule_type == "Yearly":
			if not self.month_of_year:
				frappe.throw(_("Please select month of year for Yearly schedule"))
			if not self.date_of_month:
				frappe.throw(_("Please select date of month for Yearly schedule"))
				
	def validate_based_on(self):
		if self.based_on == "Customer" and not self.customers:
			frappe.throw(_("Please add at least one customer"))
		elif self.based_on == "Customer Group" and not self.customer_groups:
			frappe.throw(_("Please add at least one customer group"))
		elif self.based_on == "Territory" and not self.territories:
			frappe.throw(_("Please add at least one territory"))
	
	def validate_date_of_month(self):
		if self.schedule_type in ["Monthly", "Quarterly", "Yearly"] and self.date_of_month:
			day = cint(self.date_of_month)
			
			if day < 1 or day > 31:
				frappe.throw(_("Date of month must be between 1 and 31"))
			
			if self.schedule_type == "Yearly" and self.month_of_year:
				month = cint(self.month_of_year)
				month_names = {
					1: "January", 2: "February", 3: "March", 4: "April",
					5: "May", 6: "June", 7: "July", 8: "August",
					9: "September", 10: "October", 11: "November", 12: "December"
				}
				months_30_days = [4, 6, 9, 11]
				
				if month == 2 and day > 29:
					frappe.throw(_("February can have maximum 29 days. Please select a date between 1 and 29"))
				elif month in months_30_days and day > 30:
					frappe.throw(_("{0} can have maximum 30 days. Please select a date between 1 and 30").format(month_names.get(month)))
				elif month == 2 and day == 29:
					frappe.msgprint(
						_("Day 29 will be skipped in February during non-leap years"),
						indicator="orange",
						alert=True
					)
			else:
				if day == 31:
					frappe.msgprint(
						_("Day 31 will be skipped in months with 30 days (April, June, September, November) and February"),
						indicator="orange",
						alert=True
					)
				elif day == 30:
					frappe.msgprint(
						_("Day 30 will be skipped in February"),
						indicator="orange",
						alert=True
					)
				elif day == 29:
					frappe.msgprint(
						_("Day 29 will be skipped in February during non-leap years"),
						indicator="orange",
						alert=True
					)
