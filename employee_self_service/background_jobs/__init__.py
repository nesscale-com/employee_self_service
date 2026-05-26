import frappe
from frappe.utils import (
    add_days,
    cint,
    flt,
    format_datetime,
    now_datetime,
    time_diff,
    today,
    get_weekday,
    getdate
)
from frappe import _
from employee_self_service.utils import (
    get_employees_having_an_event_today,
    is_holiday,
    notification_log,
)


def process_daily_ess_jobs():
    close_ess_poll()
    on_holiday_event()
    send_notification_on_event()
    process_visit_schedule_rules()


def close_ess_poll():
    try:
        filters = [
            ["poll_end_date", "=", add_days(today(), -1)],
            ["post_type", "=", "Poll"],
        ]
        ess_polls = frappe.get_all("ESS Post", filters=filters, fields=["name"])
        for row in ess_polls:
            poll_doc = frappe.get_doc("ESS Post", row.name)
            poll_doc.poll_closed = 1
            poll_doc.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(title="Close Poll Daily Job", message=frappe.get_traceback())


def on_holiday_event():
    try:
        enable_holiday_notification = frappe.db.get_single_value(
            "ESS Notification Settings", "enable_holiday_notification"
        )
        if not cint(enable_holiday_notification) == 1:
            return
        employees = frappe.get_all(
            "Employee", filters={"status": "Active"}, fields=["name", "user_id"]
        )

        user_device_info = {
            row.user_id: frappe.db.get_value(
                "Employee Device Info", row.user_id, "token"
            )
            for row in employees
            if row.user_id
        }
        for row in employees:
            if row.user_id:
                holiday, description = is_holiday(
                    row.name, today(), only_non_weekly=True, with_description=True
                )
                if holiday:
                    user_token = user_device_info.get(row.user_id)
                    if user_token:
                        notification_log(
                            "Holiday",
                            "Holiday List",
                            frappe.utils.strip_html(description[0]),
                            "Today is a holiday!",
                            row.user_id,
                            user_token,
                            "Holiday",
                        )
    except Exception:
        frappe.log_error(
            title="daily job for the holiday", message=frappe.get_traceback()
        )


def send_notification_on_event():
    try:
        enable_birthday_anniversary_notification = frappe.db.get_single_value(
            "ESS Notification Settings", "enable_birthday_anniversary_notification"
        )
        if not cint(enable_birthday_anniversary_notification) == 1:
            return
        birthday_events = get_employees_having_an_event_today("birthday", date=today())
        for event in birthday_events:
            user_token = frappe.db.get_value(
                "Employee Device Info", event.user_id, "token"
            )
            if user_token:
                template_doc = frappe.get_doc(
                    "ESS Notification Template", "Birthday Notification"
                )
                subject = frappe.render_template(
                    template_doc.get("notification_title"),
                    {"employee_name": event.name},
                )
                message = template_doc.get("notification_message")
                notification_log(
                    "Birthday", "Employee", subject, message, event.user_id, user_token
                )

        anniversary_events = get_employees_having_an_event_today(
            "work_anniversary", date=today()
        )
        for event in anniversary_events:
            user_token = frappe.db.get_value(
                "Employee Device Info", event.user_id, "token"
            )
            if user_token:
                template_doc = frappe.get_doc(
                    "ESS Notification Template", "Work Anniversary"
                )
                subject = frappe.render_template(
                    template_doc.get("notification_title"),
                    {"employee_name": event.name},
                )
                message = template_doc.get("notification_message")
                notification_log(
                    "Work Anniversary",
                    "Employee",
                    subject,
                    message,
                    event.user_id,
                    user_token,
                )
    except Exception:
        frappe.log_error(
            title="daily job for the event", message=frappe.get_traceback()
        )


def reminder_for_checkin():
    from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_details

    ess_notification_settings = frappe.get_doc(
        "ESS Notification Settings", "ESS Notification Settings"
    )

    # Check if the reminder setting is enabled
    if (
        not ess_notification_settings.enable_check_in_reminder
        or flt(ess_notification_settings.check_in_reminder_after) <= 0
    ):
        return
    shifts = frappe.get_all("Shift Type", filters={}, fields=["name"])
    for shift in shifts:
        try:
            if frappe.db.exists(
                "ESS Reminder Log",
                {"date": today(), "log_type": "IN", "shift": shift.name},
            ):
                continue
            shift_details = get_shift_details(shift.name)
            # Convert datetime to string format that `time_diff_in_minutes` accepts
            now_str = format_datetime(now_datetime(), "yyyy-MM-dd HH:mm:ss")
            start_str = format_datetime(
                shift_details.get("start_datetime"), "yyyy-MM-dd HH:mm:ss"
            )
            # Calculate time difference
            diff_minutes = time_diff_in_minutes(now_str, start_str)
            # Check if they are late based on configured threshold
            if diff_minutes > flt(
                ess_notification_settings.get("check_in_reminder_after")
            ):
                # Fetch employees who have already checked in today
                logs_employee = frappe.db.sql(
                    """
					SELECT DISTINCT employee
					FROM `tabEmployee Checkin`
					WHERE log_type = 'IN'
					AND DATE(time) = %s
				""",
                    today(),
                    as_dict=True,
                )

                checkedin_employees = [row.employee for row in logs_employee]
                employees = get_assigned_employees(
                    shift.name, today(), checkedin_employees
                )
                template_doc = frappe.get_doc(
                    "ESS Notification Template", "Missed Checkin Reminder"
                )
                for row in employees:
                    subject = frappe.render_template(
                        template_doc.get("notification_title"), row
                    )
                    message = frappe.render_template(
                        template_doc.get("notification_message"), row
                    )
                    user_token = frappe.db.get_value(
                        "Employee Device Info", row.user_id, "token"
                    )
                    if not user_token:
                        continue

                    # Check if today is a holiday for the employee
                    if is_on_holiday_or_leave(row.name):
                        continue
                    notification_log(
                        "Checkin Reminder",
                        "Employee",
                        subject,
                        message,
                        row.user_id,
                        user_token,
                    )
                create_ess_reminder_log("IN", "Completed", shift.name)
        except Exception:
            create_ess_reminder_log("IN", "Failed", shift.name)
            frappe.log_error(
                title="Error in Check-in Reminder", message=frappe.get_traceback()
            )


def reminder_for_checkout():
    from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_details

    ess_notification_settings = frappe.get_doc(
        "ESS Notification Settings", "ESS Notification Settings"
    )

    # Check if the reminder setting is enabled
    if (
        not ess_notification_settings.enable_check_in_reminder
        or flt(ess_notification_settings.check_in_reminder_after) <= 0
    ):
        return
    shifts = frappe.get_all("Shift Type", filters={}, fields=["name"])
    for shift in shifts:
        try:
            if frappe.db.exists(
                "ESS Reminder Log",
                {"date": today(), "log_type": "OUT", "shift": shift.name},
            ):
                continue
            shift_details = get_shift_details(shift.name)
            # Convert datetime to string format that `time_diff_in_minutes` accepts
            now_str = format_datetime(now_datetime(), "yyyy-MM-dd HH:mm:ss")
            end_str = format_datetime(
                shift_details.get("end_datetime"), "yyyy-MM-dd HH:mm:ss"
            )

            # Calculate time difference
            diff_minutes = time_diff_in_minutes(now_str, end_str)
            # Check if they are late based on configured threshold
            if diff_minutes > flt(
                ess_notification_settings.get("check_out_reminder_after")
            ):
                # Fetch employees who have already checked in today
                logs_employee = frappe.db.sql(
                    """
					SELECT DISTINCT employee
					FROM `tabEmployee Checkin`
					WHERE log_type = 'OUT'
					AND DATE(time) = %s
				""",
                    today(),
                    as_dict=True,
                )

                checkedout_employees = [row.employee for row in logs_employee]
                employees = get_assigned_employees(
                    shift.name, today(), checkedout_employees
                )

                template_doc = frappe.get_doc(
                    "ESS Notification Template", "Missed Checkout Reminder"
                )
                for row in employees:
                    subject = frappe.render_template(
                        template_doc.get("notification_title"), row
                    )
                    message = frappe.render_template(
                        template_doc.get("notification_message"), row
                    )
                    user_token = frappe.db.get_value(
                        "Employee Device Info", row.user_id, "token"
                    )
                    if not user_token:
                        continue

                    if not shift_details.get("end_datetime"):
                        continue

                    # Check if today is a holiday for the employee
                    if is_on_holiday_or_leave(row.name):
                        continue
                    notification_log(
                        "Checkout Reminder",
                        "Employee",
                        subject,
                        message,
                        row.user_id,
                        user_token,
                    )
                create_ess_reminder_log("OUT", "Completed", shift.name)
        except Exception:
            create_ess_reminder_log("OUT", "Failed", shift.name)
            frappe.log_error(
                title="Error in Check-out Reminder", message=frappe.get_traceback()
            )


def time_diff_in_minutes(string_end_date, string_start_date):
    """
    Calculate the time difference in minutes between two datetime strings using frappe.utils.time_diff.
    """
    return time_diff(string_end_date, string_start_date).total_seconds() / 60


def is_on_holiday_or_leave(employee):
    """
    Returns True if the employee has a holiday or an approved leave today.
    """
    if frappe.db.exists(
        "Leave Application",
        {
            "employee": employee,
            "status": "Approved",
            "from_date": ["<=", today()],
            "to_date": [">=", today()],
        },
    ):
        return True

    holiday, _ = is_holiday(
        employee, today(), only_non_weekly=True, with_description=True
    )
    return holiday


def create_ess_reminder_log(log_type, status, shift):
    frappe.get_doc(
        doctype="ESS Reminder Log",
        date=today(),
        log_type=log_type,
        status=status,
        shift=shift,
    ).insert(ignore_permissions=True)


def get_assigned_employees(shift, date, checkedin_employees):
    filters = [
        ["shift_type", "=", shift],
        ["docstatus", "=", 1],
        ["status", "=", "Active"],
        ["employee", "not in", checkedin_employees],
    ]
    or_filters = [["end_date", ">=", date], ["end_date", "is", "not set"]]

    # Get assigned employees
    assigned_employees = frappe.get_all(
        "Shift Assignment", filters=filters, or_filters=or_filters, pluck="employee"
    )

    default_shift_filters = [
        ["default_shift", "=", shift],
        ["status", "=", "Active"],
        ["name", "not in", assigned_employees],
        ["name", "not in", checkedin_employees],
    ]
    default_shift_employees = frappe.get_all(
        "Employee", filters=default_shift_filters, pluck="employee"
    )

    assigned_employees.extend(default_shift_employees)

    # Fetch user IDs for the final employee list
    final_employees = frappe.get_all(
        "Employee",
        filters={"name": ["in", assigned_employees], "status": "Active"},
        fields=["name as employee", "user_id", "employee_name"],
    )

    return final_employees


def process_visit_schedule_rules():
    try:
        settings = frappe.get_single("ESS Field Staff Settings")
        create_todo = settings.visit_schedule_create_todo
        
        rules = frappe.get_all(
            "ESS Visit Schedule Rule",
            filters={"enabled": 1},
            pluck="name"
        )
        
        for rule in rules:
            rule_doc = frappe.get_doc("ESS Visit Schedule Rule", rule)
            if not should_process_rule(rule_doc):
                continue
            
            customers = get_customers_from_rule(rule_doc)
            for customer in customers:
                if create_todo:
                    create_visit_todo(rule_doc, customer)
                else:
                    create_visit_record(rule_doc, customer)   
    except Exception:
        frappe.log_error(title="Process Visit Schedule Rules", message=frappe.get_traceback())

def should_process_rule(rule_doc):    
    current_date = getdate(today())
    schedule_type = rule_doc.schedule_type
    
    if schedule_type == "Daily":
        weekday_map = {
            0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday",
            4: "friday", 5: "saturday", 6: "sunday"
        }
        weekday_field = weekday_map.get(current_date.weekday())
        return rule_doc.get(weekday_field) == 1
        
    elif schedule_type == "Weekly":
        return current_date.strftime("%A") == rule_doc.day_of_week
        
    elif schedule_type == "Fortnightly":
        if current_date.strftime("%A") == rule_doc.day_of_week:
            day_of_month = current_date.day
            return (day_of_month <= 7) or (15 <= day_of_month <= 21)
        
    elif schedule_type == "Monthly":
        expected_day = cint(rule_doc.date_of_month)
        return cint(current_date.day) == expected_day
        
    elif schedule_type == "Quarterly":
        quarter_months = {
            1: [1, 2, 3],
            2: [4, 5, 6],
            3: [7, 8, 9],
            4: [10, 11, 12]
        }
        expected_quarter = cint(rule_doc.quarter)
        return (
            current_date.month in quarter_months.get(expected_quarter, [])
            and cint(current_date.day) == cint(rule_doc.date_of_month)
        )
        
    elif schedule_type == "Yearly":
        return cint(current_date.day) == cint(rule_doc.date_of_month) and cint(current_date.month) == cint(rule_doc.month_of_year)
        
    return False


def get_customers_from_rule(rule_doc):
    customers = []
    
    if rule_doc.based_on == "Customer":
        customers = [row.customer for row in rule_doc.customers]
        
    elif rule_doc.based_on == "Customer Group":
        customer_groups = [row.customer_group for row in rule_doc.customer_groups]
        customers = frappe.get_all(
            "Customer",
            filters={"customer_group": ["in", customer_groups]},
            pluck="name"
        )
        
    elif rule_doc.based_on == "Territory":
        territories = [row.territory for row in rule_doc.territories]
        customers = frappe.get_all(
            "Customer",
            filters={"territory": ["in", territories]},
            pluck="name"
        )
        
    return customers


def create_visit_todo(rule_doc, customer):
    if frappe.db.exists("ToDo", {
        "reference_type": "ESS Visit Schedule Rule",
        "reference_name": rule_doc.name,
        "allocated_to": rule_doc.user,
        "date": today(),
        "description": ["like", f"%{customer}%"]
    }):
        return
    
    customer_name = frappe.db.get_value("Customer", customer, "customer_name") or customer
    
    todo = frappe.get_doc({
        "doctype": "ToDo",
        "reference_type": "ESS Visit Schedule Rule",
        "reference_name": rule_doc.name,
        "allocated_to": rule_doc.user,
        "date": today(),
        "description": f"Visit scheduled for customer: {customer_name}",
        "priority": "Medium",
        "status": "Open"
    })
    todo.insert(ignore_permissions=True)

def create_visit_record(rule_doc, customer):
    if frappe.db.exists("ESS Visit", {
        "employee": rule_doc.employee,
        "customer": customer,
        "date": today(),
        "auto_created_from_rule": 1
    }):
        return
    
    visit = frappe.get_doc({
        "doctype": "ESS Visit", 
        "customer_type": "Existing",
        "customer": customer,
        "employee": rule_doc.employee,
        "user": rule_doc.user,
        "date": today(),
        "visit_type": rule_doc.visit_type,
        "status": "Pending",
        "auto_created_from_rule": 1,
        "description": f"Auto-scheduled visit from rule: {rule_doc.rule_name}"
    })
    visit.insert(ignore_permissions=True)

