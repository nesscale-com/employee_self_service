import frappe
from frappe import _


def get_employee_from_sales_team(doctype, docname):
    sales_persons = frappe.get_all(
        "Sales Team",
        filters={"parenttype": doctype, "parent": docname},
        fields=["sales_person"],
    )
    employees = []
    for sp in sales_persons:
        emp = frappe.db.get_value("Sales Person", sp.sales_person, "employee")
        if emp:
            employees.append(emp)
    return employees
