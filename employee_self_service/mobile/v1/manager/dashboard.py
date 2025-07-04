import frappe
import json
from frappe import _
from frappe.utils import *
from erpnext.accounts.utils import get_fiscal_year
from erpnext import get_default_company
from employee_self_service.mobile.v1.api_utils import *
from employee_self_service.mobile.v1.manager.manager_utils import get_action


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

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_crm_dashboard():
    fiscal_year, fy_start, fy_end = get_fiscal_year(today())
    company = get_default_company()

    current_month_start = get_first_day(today())
    current_month_end = get_last_day(today())
    previous_month_start = get_first_day(add_months(today(), -1))
    previous_month_end = get_last_day(add_months(today(), -1))

    def get_deals(filters, fields=None):
        return frappe.get_list("Opportunity", filters=filters, fields=fields)

    def get_pipeline_deals(start_date, end_date):
        return get_deals(
            filters=[
                ["transaction_date", "between", [start_date, end_date]],
                ["status", "not in", ["Lost", "Closed", "Converted"]],
                ["company", "=", company]
            ],
            fields=["opportunity_amount"]
        )

    def calculate_percentage_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 2)

    # Fetch Deal Lists
    deals_closed = get_deals([
        ["transaction_date", "between", [fy_start, fy_end]],
        ["status", "=", "Converted"],
        ["company", "=", company]
    ], fields=["name"])

    total_deals = get_deals([
        ["company", "=", company]
    ], fields=["name"])

    lost_deals = get_deals([
        ["transaction_date", "between", [fy_start, fy_end]],
        ["status", "=", "Lost"],
        ["company", "=", company]
    ], fields=["name"])

    stopped_deals = get_deals([
        ["transaction_date", "between", [fy_start, fy_end]],
        ["status", "=", "Closed"],
        ["company", "=", company]
    ], fields=["name"])

    # Pipeline Data
    pipeline_deals = get_pipeline_deals(fy_start, fy_end)
    current_pipeline = get_pipeline_deals(current_month_start, current_month_end)
    previous_pipeline = get_pipeline_deals(previous_month_start, previous_month_end)

    total_pipeline_amount = sum(flt(d.opportunity_amount) for d in pipeline_deals)
    current_amount = sum(flt(d.opportunity_amount) for d in current_pipeline)
    previous_amount = sum(flt(d.opportunity_amount) for d in previous_pipeline)

    percent_change = calculate_percentage_change(current_amount, previous_amount)
    deal_count_change = calculate_percentage_change(len(current_pipeline), len(previous_pipeline))

    # Final Dashboard Response
    # Determine color based on percent_change
    if percent_change > 0:
        color = "#28a745"  # green
    elif percent_change < 0:
        color = "#dc3545"  # red
    elif percent_change == 0:
        color = "#FFA500"  # orange
    else:
        color = "#111111"  # black

    dashboard = [
        {
            "title": "Deals Closed (Current FY)",
            "value": len(deals_closed),
        },
        {
            "title": "Total Number of Deals",
            "value": len(total_deals),
        },
        {
            "title": "Amount in Pipeline",
            "value": total_pipeline_amount,
            "subtext": f"{percent_change}% from last month",
            "color": color
        },
        {
            "title": "Deals in Pipeline",
            "value": len(pipeline_deals),
            "subtext": f"{deal_count_change}% from last month",
            "color": color
        },
        {
            "title": "Lost Opportunities",
            "value": len(lost_deals),
        },
        {
            "title": "Deals Stopped",
            "value": len(stopped_deals),
        }
    ]

    return gen_response(200, "CRM Dashboard Stats fetched successfully", dashboard)



def calculate_percentage_change(current, previous):
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_procurement_dashboard(filter_by="monthly"):
    """
    Fetch Procurement dashboard data with filters: monthly, quarterly, yearly.
    
    Args:
    filter_by (str): Filter for data, values can be 'monthly', 'quarterly', 'yearly'. Default is 'monthly'.

    Returns:
    dict: Procurement dashboard data based on the selected filter.
    """
    data = {
        "monthly": {
            "duration": ["Jan", "Feb"],
            "cashflow_values": [200, 300],
            "receivable": 200,
            "payable": 68
        },
        "quarterly": {
            "duration": ["Q1", "Q2", "Q3", "Q4"],
            "cashflow_values": [500, 600, 550, 700],
            "receivable": 2000,
            "payable": 680
        },
        "yearly": {
            "duration": ["2024"],
            "cashflow_values": [2400],
            "receivable": 8000,
            "payable": 2720
        }
    }

    if filter_by not in data:
        frappe.throw(_("Invalid filter. Use 'monthly', 'quarterly', or 'yearly'."))

    filtered_data = data[filter_by]

    place_holder_data = {
            "CashflowOverview": {
                "duration": filtered_data["duration"],
                "values1": filtered_data["cashflow_values"],
                "values2": filtered_data["cashflow_values"]
            },
            "AccountsReceivablePayable": {
                "Receivable": filtered_data["receivable"],
                "Payable": filtered_data["payable"]
            }
    }
    return gen_response(200, "Stats get successfully", place_holder_data)

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
