import frappe

MOBILE_APP_ROUTES = [
    {
        "in_detail_view": 0,
        "doctype_reference": "Expense Claim",
        "app_route": "/main/home/my-expenses",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Expense Claim",
        "app_route": "/main/home/my-expenses/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Leave Application",
        "app_route": "/main/home/my-leave",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Leave Application",
        "app_route": "/main/home/my-leave/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Sales Order",
        "app_route": "/main/home/orders",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Sales Order",
        "app_route": "/main/home/orders/{id}",
    },
    {"in_detail_view": 0, "doctype_reference": "Task", "app_route": "/main/home/tasks"},
    {
        "in_detail_view": 1,
        "doctype_reference": "Task",
        "app_route": "/main/home/tasks/{id}",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "ESS Post",
        "app_route": "/main/home/post/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Attendance Request",
        "app_route": "/main/home/attendance-request",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Attendance Request",
        "app_route": "/main/home/attendance-request/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Quotation",
        "app_route": "/main/home/quotations",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Quotation",
        "app_route": "/main/home/quotations/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Payment Entry",
        "app_route": "/main/home/payment-entries",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Payment Entry",
        "app_route": "/main/home/payment-entries/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Shift Request",
        "app_route": "/main/home/shift-request",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Shift Request",
        "app_route": "/main/home/shift-request/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Timesheet",
        "app_route": "/main/home/timesheet",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Timesheet",
        "app_route": "/main/home/timesheet/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Lead",
        "app_route": "/main/home/leads",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Lead",
        "app_route": "/main/home/leads/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "Issue",
        "app_route": "/main/home/issue",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "Issue",
        "app_route": "/main/home/issue/{id}",
    },
    {
        "in_detail_view": 0,
        "doctype_reference": "ToDo",
        "app_route": "/main/home/todo",
    },
    {
        "in_detail_view": 1,
        "doctype_reference": "ToDo",
        "app_route": "/main/home/todo/{id}",
    },
]
