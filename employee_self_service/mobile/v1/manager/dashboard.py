import frappe
import json
from frappe import _
from frappe.utils import pretty_date, getdate, fmt_money
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    remove_default_fields,
    get_global_defaults,
)
from employee_self_service.mobile.v1.manager.manager_utils import get_action


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_dashboard_stats():
    try:
        stats = {
            "clock_in": 48,
            "clock_out": 10,
            "not_clock_in": 7,
            "on_leave": 10,
            "approval": 13,
            "tasks": 40
        }
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
def get_crm_dashboard(filter_by="monthly"):
    """
    Fetch CRM dashboard data with filters: monthly, quarterly, yearly.
    
    Args:
    filter_by (str): Filter for data, values can be 'monthly', 'quarterly', 'yearly'. Default is 'monthly'.

    Returns:
    dict: CRM dashboard data based on the selected filter.
    """
    data = {
        "monthly": {
            "duration": ["Jan", "Feb", "Mar"],
            "lead_conversion_rate": [20, 15, 10],
            "total_sales": [200, 400, 450]
        },
        "quarterly": {
            "duration": ["Q1", "Q2", "Q3", "Q4"],
            "lead_conversion_rate": [45, 60, 50, 70],
            "total_sales": [1050, 1200, 950, 1300]
        },
        "yearly": {
            "duration": ["2024"],
            "lead_conversion_rate": [225],
            "total_sales": [4500]
        }
    }

    if filter_by not in data:
        frappe.throw(_("Invalid filter. Use 'monthly', 'quarterly', or 'yearly'."))

    filtered_data = data[filter_by]
    
    place_holder_data =  {
            "TotalLead": 200,  # Static for placeholder
            "LeadConversionRate": {
                "duration": filtered_data["duration"],
                "values": filtered_data["lead_conversion_rate"]
            },
            "TotalSales": {
                "numberOfTotalSales": sum(filtered_data["total_sales"]),
                "duration": filtered_data["duration"],
                "values": filtered_data["total_sales"]
            }
    }
    return gen_response(200, "Stats get successfully", place_holder_data)


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
                "total_emp": 502,
                "active_emp": 402,
                "new_emp": 100
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
                "new_hires": 22,
                "terminates": 10
            }
        
    }
    return gen_response(200, "Stats get successfully", place_holder_data)
