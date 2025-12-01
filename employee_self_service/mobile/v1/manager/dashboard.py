import frappe
import json
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from erpnext import get_default_company
from employee_self_service.mobile.v1.api_utils import *
from employee_self_service.mobile.v1.manager.manager_utils import get_action
from frappe.desk.doctype.number_card.number_card import get_result
from frappe.desk.doctype.number_card.number_card import get_percentage_difference

from frappe.utils import *


stats_qualifier_map = {
	"Daily": _("since yesterday"),
	"Weekly": _("since last week"),
	"Monthly": _("since last month"),
	"Yearly": _("since last year"),
}

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats():
	try:
		stats = {
			"total_employees": 0,
			"clock_in": 0,
			"clock_out": 0,
			"on_leave": 0,
			"not_clock_in": 0,
		}

		# Step-1: Get all employees that current user has permission to access
		employee_list = frappe.get_list("Employee", pluck="name")
		
		if not employee_list:
			frappe.throw(_("No employees found"))
		
		stats["total_employees"] = len(employee_list)
		
		# Step-2: Get all check-ins for today for these employees
		checkins_today = frappe.get_all("Employee Checkin",
							filters={
								"time": ["between", [f"{today()} 00:00:00", f"{today()} 23:59:59"]],
								"employee": ["in", employee_list]
							},
							fields=["employee", "log_type"])
		
		employee_check_in_today = [emp["employee"] for emp in checkins_today]

		for checkin in checkins_today:
			if checkin["log_type"] == "IN":
				stats["clock_in"] += 1
			elif checkin["log_type"] == "OUT":
				stats["clock_out"] += 1
		
		# Step-3: Get leave applications for these employees
		employees_on_leave = frappe.get_all("Leave Application",
								filters={
									"status": "Approved",
									"docstatus": 1,
									"from_date": ["<=", today()],
									"to_date": [">=", today()],
									"employee": ["in", employee_list]
								},
								pluck="employee")
		
		stats["on_leave"] = len(employees_on_leave)

		# Step-4: Get not_clock_in employees
		for emp in employee_list:
			if emp not in employee_check_in_today:
				stats["not_clock_in"] += 1

		return gen_response(200, "Stats get successfully", stats)
	except Exception as e:
		return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats_list(type):
	try:
		data = [
			{
				"image": "/files/logo.svg" ,
				"name": "Nilesh Makwana"
			},
			{
				"image": "/files/logo.svg" ,
				"name": "Nilesh Makwana"
			},
			{
				"image": "/files/logo.svg" ,
				"name": "Nilesh Makwana"
			},
			{
				"image": "/files/logo.svg" ,
				"name": "Nilesh Makwana"
			},
			{
				"image": "/files/logo.svg" ,
				"name": "Nilesh Makwana"
			},
		]
		return gen_response(200, "Stats get successfully", data)
	except Exception as e:
		return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_accounting_dashboard(filter_by="monthly"):
	"""
	Fetch accounting dashboard data with filters: monthly, quarterly, yearly.
	
	Args:
	filter_by (str): Filter for data, values can be 'monthly', 'quarterly', 'yearly'. Default is 'monthly'.

	Returns:
	dict: Accounting dashboard data based on the selected filter.
	"""
	# Define placeholder data
	# income, expense, profit
	# in profit loss only value of profit is shown
	data = {
		"monthly": {
			"duration": ["Jan", "Feb", "Mar"],
			"cashflow_values": [10000, 15000, 12000],
			"accounts_values": [8000, 12000, 10000],
			"revenue_expenses": {
				"income": [150000, 180000, 120000],
				"expense": [2000, 2500, 1500],
				"profit": [148000, 177500, 118500]
			},
			"profit_loss": [
				[150000, 2000, 148000],
				[180000, 2500, 177500],
				[120000, 1500, 118500]
			],
			"profit": [148000, 177500, 118500]
		},
		"quarterly": {
			"duration": ["Q1", "Q2", "Q3", "Q4"],
			"cashflow_values": [50000, 60000, 45000, 70000],
			"accounts_values": [40000, 50000, 35000, 60000],
			"revenue_expenses": {
				"income": [450000, 540000, 360000],
				"expense": [6000, 7500, 5000],
				"profit": [444000, 532500, 355000]
			},
			"profit_loss": [
				[450000, 6000, 444000],
				[540000, 7500, 532500],
				[360000, 5000, 355000]
			],
			"profit": [444000, 532500, 355000]
		},
		"yearly": {
			"duration": ["2024"],
			"cashflow_values": [300000],
			"accounts_values": [200000],
			"revenue_expenses": [
				[1800000, 24000, 1776000]
			],
			"profit_loss": [
				[1800000, 24000, 1776000]
			],
		}
	}

	# Validate filter
	if filter_by not in data:
		frappe.throw(_("Invalid filter. Use 'monthly', 'quarterly', or 'yearly'."))

	# Fetch filtered data
	filtered_data = data[filter_by]

	# Format the response
	
	place_holder_data = {
			"CashflowOverview": {
				"duration": filtered_data["duration"],
				"values1": filtered_data["cashflow_values"],
				"values2": filtered_data["cashflow_values"]
			},
			"AccountsReceivablePayable": {
				"duration": filtered_data["duration"],
				"values1": filtered_data["accounts_values"],
				"values2": filtered_data["accounts_values"]
			},
			"RevenueAndExpenses": {
				"TotalIncome": sum(item for item in filtered_data["revenue_expenses"]['income']),
				"TotalExpense": sum(item for item in filtered_data["revenue_expenses"]['expense']),
				"NetProfit": sum(item for item in filtered_data["revenue_expenses"]['profit']),
				"duration": filtered_data["duration"],
				"income": filtered_data["revenue_expenses"]['income'],
				"expense": filtered_data["revenue_expenses"]['expense'],
				"profit": filtered_data["revenue_expenses"]['profit'],
			},
			"ProfitAndLoss": {
				"TotalIncome": sum(item[0] for item in filtered_data["profit_loss"]),
				"TotalExpense": sum(item[1] for item in filtered_data["profit_loss"]),
				"NetProfit": sum(item[2] for item in filtered_data["profit_loss"]),
				"duration": filtered_data["duration"],
				"profit": filtered_data["profit"]
			}
	}
	return gen_response(200, "Stats get successfully", place_holder_data)



def get_all_filters(doc):
	filters = json.loads(doc.filters_json) if doc.filters_json else []
	dynamic_filters = json.loads(doc.dynamic_filters_json) if doc.dynamic_filters_json else None

	if not dynamic_filters or not bool(dynamic_filters):
		return filters

	if isinstance(dynamic_filters, list):
		for f in dynamic_filters:
			try:
				# Evaluate the expression in f[3]
				f[3] = eval(f[3], {}, {})
			except Exception as e:
				frappe.throw(f"Invalid expression set in filter {f[1]} ({f[0]}): {e}")
		filters.extend(dynamic_filters)
	elif isinstance(dynamic_filters, dict):
		for key in dynamic_filters:
			try:
				val = eval(dynamic_filters[key], {}, {})
				dynamic_filters[key] = val
			except Exception as e:
				frappe.throw(f"Invalid expression set in filter {key}: {e}")
		if isinstance(filters, dict):
			filters.update(dynamic_filters)
		elif isinstance(filters, list):
			# Convert dict to list format if filters is list
			filters.extend([[k, "=", v] for k, v in dynamic_filters.items()])
		else:
			filters = dynamic_filters
	return filters


def format_number_for_card(card_doc, number):
	country = frappe.db.get_value("System Settings","System Settings","country")
	
	if card_doc.get("show_full_number"):
		main = str(number)
		symbol = ""
	else:
		short = shorten_number(flt(number), country=country,precision=2, currency=card_doc.get("currency"))
		parts = short.split(" ")
		main = parts[0]
		symbol = parts[1] if len(parts) > 1 else ""
	
	if card_doc.get("currency"):
		formatted_main = fmt_money(main, currency=card_doc.currency)
		return f"{formatted_main} {symbol}".strip()
	
	return f"{main} {symbol}".strip()


def shorten_number(number, country=None, precision=2, currency=False):
	"""
	Returns a shortened version of a number based on the country formatting style.
	- For India: "Lac", "Cr"
	- For others: "K", "M", "B", etc.
	"""
	if number is None:
		return "0"

	number = float(number)

	if country in ["India", "Pakistan", "Bangladesh", "Myanmar"]:
		divisors = [
			(1_00_00_000, "Cr"),
			(1_00_000, "Lac"),
			(1_000, "K"),
		]
	else:
		divisors = [
			(1_000_000_000, "B"),
			(1_000_000, "M"),
			(1_000, "K"),
		]

	for divisor, suffix in divisors:
		if abs(number) >= divisor:
			if currency:
				value = round(number / divisor, precision)
			else:
				value = round(number / divisor)
			return f"{value} {suffix}"

	if currency:
		return str(round(number, precision))
	else:
		return str(round(number))


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_crm_dashboard(company='securetech'):
	if company == 'nx_digital':
		number_card_names = [
			"Deals Closed (NX- FY - 24)-1",
			"Deals Closed NX # (Current FY)-1",
			"Amount in Pipeline NX 25",
			"Deals in Pipeline NX-1",
			"Lost Opportunity NX",
			"Deals Stopped NX"
		]
	else:
		number_card_names = [
			"Deals Closed (FY - 25)",
			"Deals Closed # (Current FY)-1",
			"Amount in Pipeline 25",
			"Deals in Pipeline-1",
			"Lost Opportunity",
			"Deals Stopped"
		]

	dashboard = []

	for name in number_card_names:
		doc = frappe.get_doc("Number Card", name)
		filters = get_all_filters(doc)
		result = get_result(doc=doc, filters=filters)
		percentage = shorten_number(get_percentage_difference(doc, filters, result), currency = doc.get('currency'))
		stats_qualifier = stats_qualifier_map.get(doc.get("stats_time_interval"), "")
		percentage_text = f"{percentage} % {stats_qualifier}".strip()

		card = {
			"title": doc.label or doc.name,
			"value": format_number_for_card(doc, result),
		}

		# Add subtext and color only for time-based comparison
		if doc.stats_time_interval and doc.stats_time_interval != "Last":
			card["subtext"] = percentage_text

			if isinstance(percentage, (int, float, str)) and str(percentage).replace('%', '').replace('.', '').isdigit():
				num = float(str(percentage).replace('%', ''))
				if num > 0:
					card["color"] = "0xff28a745"  # green
				elif num < 0:
					card["color"] = "0xffdc3545"  # red
				else:
					card["color"] = "0xffFFA500"  # orange
			else:
				card["color"] = "0xff111111"  # fallback color

		dashboard.append(card)

	return gen_response(200, "CRM Dashboard Stats fetched successfully", dashboard)

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_hr_dashboard():
	"""
	Fetch HR dashboard data without filters.

	Returns:
	dict: HR dashboard data.
	"""
	place_holder_data = {
		"employee_count": {
			"total_emp": 0,
			"active_emp": 0,
			"inactive_emp": 0
		},
		"turnover_rate": {
			"turnover_rate": 10,
			"annualized": 40,
			"aug_emp": 100
		},
		"AbsenteeismRate": {
			"absenteeism_rate": 4.3,
			"work_days": 231,
			"off_days": 31
		},
		"Hire_and_Terminates": {
			"new_hires": 0,
			"terminates": 0
		}  
	}

	# Fetch all employees 
	employee_list = frappe.get_list(
		"Employee",
		fields=["status", "relieving_date", "date_of_joining"]
	)

	for emp in employee_list:
		place_holder_data["employee_count"]["total_emp"] += 1
		
		# Status check
		if emp.status == "Active":
			place_holder_data["employee_count"]["active_emp"] += 1
		else:
			place_holder_data["employee_count"]["inactive_emp"] += 1

		# New hires in last 30 days
		if emp.date_of_joining and getdate(emp.date_of_joining) >= getdate(add_days(today(), -30)):
			place_holder_data["Hire_and_Terminates"]["new_hires"] += 1

		# Terminations in last 30 days
		if emp.relieving_date and getdate(emp.relieving_date) >= getdate(add_days(today(), -30)):
			place_holder_data["Hire_and_Terminates"]["terminates"] += 1

	return gen_response(200, "HR Dashboard Stats get successfully", place_holder_data)
