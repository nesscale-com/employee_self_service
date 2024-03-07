from . import __version__ as app_version

app_name = "employee_self_service"
app_title = "Employee Self Service"
app_publisher = "Nesscale Solutions Private Limited"
app_description = "Employee Self Service"
app_email = "info@nesscale.com"
app_license = "MIT"

# Includes in <head>
# ------------------

after_install = "employee_self_service.setup.after_install"
after_migrate = "employee_self_service.setup.after_install"


# include js, css files in header of desk.html
# app_include_css = "/assets/employee_self_service/css/employee_self_service.css"
# app_include_js = "/assets/employee_self_service/js/employee_self_service.js"

# include js, css files in header of web template
# web_include_css = "/assets/employee_self_service/css/employee_self_service.css"
# web_include_js = "/assets/employee_self_service/js/employee_self_service.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "employee_self_service/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Employee Checkin": "public/js/employee_checkin.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "employee_self_service.utils.jinja_methods",
# 	"filters": "employee_self_service.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "employee_self_service.install.before_install"
# after_install = "employee_self_service.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "employee_self_service.uninstall.before_uninstall"
# after_uninstall = "employee_self_service.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "employee_self_service.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
    "Leave Application": {
        "on_update": "employee_self_service.mobile.ess.on_leave_application_update"
    },
    "Expense Claim": {
        "on_submit": "employee_self_service.mobile.ess.on_expense_submit"
    },
    "ToDo": {
        "after_insert": "employee_self_service.mobile.ess.send_notification_for_task_assign"
    },
    # "Comment": {
    #     "after_insert": "employee_self_service.mobile.ess.send_notification_on_task_comment"
    # },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": ["employee_self_service.mobile.ess.daily_notice_board_event"],
    "cron": {
        "0 9 * * *": ["employee_self_service.mobile.ess.send_notification_on_event"],
        "0 9 * * *": ["employee_self_service.mobile.ess.on_holiday_event"],
    },
}

# Testing
# -------

# before_tests = "employee_self_service.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "employee_self_service.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "employee_self_service.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"employee_self_service.auth.validate"
# ]

fixtures = [
    {
        "dt": "Notice Board Template",
    },
    {
        "dt": "Notice Board Template Type",
    },
    {"dt": "Custom DocPerm", "filters": [["name", "in", ["5318c19ff9", "c3d5dc5296"]]]},
    {
        "dt": "Ess Translation",
    },
]
