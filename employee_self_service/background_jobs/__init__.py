import frappe
from frappe.utils import (
    add_days,
    cint,
    flt,
    format_datetime,
    now_datetime,
    time_diff,
    today,
)

from employee_self_service.utils import (
    get_employees_having_an_event_today,
    is_holiday,
    notification_log,
)


def process_daily_ess_jobs():
    close_ess_poll()
    on_holiday_event()
    send_notification_on_event()


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
            now_str = format_datetime(now_datetime(), "yyyy-MM-dd HH:mm:ss")
            start_str = format_datetime(
                shift_details.get("start_datetime"), "yyyy-MM-dd HH:mm:ss"
            )
            diff_minutes = time_diff_in_minutes(now_str, start_str)
            if diff_minutes > flt(ess_notification_settings.get("check_in_reminder_after")):
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
                employees = get_assigned_employees(shift.name, today(), checkedin_employees)

                employees_to_skip = (
                    get_employees_to_skip([row.employee for row in employees])
                    if cint(ess_notification_settings.exclude_employees_on_holiday_or_leave)
                    else set()
                )

                template_doc = frappe.get_doc(
                    "ESS Notification Template", "Missed Checkin Reminder"
                )
                for row in employees:
                    if row.employee in employees_to_skip:
                        continue
                    user_token = frappe.db.get_value(
                        "Employee Device Info", row.user_id, "token"
                    )
                    if not user_token:
                        continue
                    subject = frappe.render_template(
                        template_doc.get("notification_title"), row
                    )
                    message = frappe.render_template(
                        template_doc.get("notification_message"), row
                    )
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
            if not shift_details.get("end_datetime"):
                continue
            now_str = format_datetime(now_datetime(), "yyyy-MM-dd HH:mm:ss")
            end_str = format_datetime(
                shift_details.get("end_datetime"), "yyyy-MM-dd HH:mm:ss"
            )
            diff_minutes = time_diff_in_minutes(now_str, end_str)
            if diff_minutes > flt(ess_notification_settings.get("check_out_reminder_after")):
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
                employees = get_assigned_employees(shift.name, today(), checkedout_employees)

                employees_to_skip = (
                    get_employees_to_skip([row.employee for row in employees])
                    if cint(ess_notification_settings.exclude_employees_on_holiday_or_leave)
                    else set()
                )

                template_doc = frappe.get_doc(
                    "ESS Notification Template", "Missed Checkout Reminder"
                )
                for row in employees:
                    if row.employee in employees_to_skip:
                        continue
                    user_token = frappe.db.get_value(
                        "Employee Device Info", row.user_id, "token"
                    )
                    if not user_token:
                        continue
                    subject = frappe.render_template(
                        template_doc.get("notification_title"), row
                    )
                    message = frappe.render_template(
                        template_doc.get("notification_message"), row
                    )
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


def get_employees_to_skip(employee_names):
    """
    Returns a set of employee IDs who should not receive a reminder today
    because they are on approved leave or on a holiday.
    Uses bulk queries instead of per-employee lookups.
    """
    if not employee_names:
        return set()

    today_date = today()

    # 1 query: all employees on approved leave today
    on_leave = set(
        frappe.get_all(
            "Leave Application",
            filters={
                "employee": ["in", employee_names],
                "status": "Approved",
                "from_date": ["<=", today_date],
                "to_date": [">=", today_date],
            },
            pluck="employee",
        )
    )

    # 1 query: all holiday lists that have today as a holiday (weekly off or not)
    holiday_lists_today = set(
        frappe.get_all(
            "Holiday",
            filters={"holiday_date": today_date},
            pluck="parent",
        )
    )

    on_holiday = set()
    if holiday_lists_today:
        # 1 query: get each employee's holiday list and company
        emp_data = frappe.get_all(
            "Employee",
            filters={"name": ["in", employee_names]},
            fields=["name", "holiday_list", "company"],
        )

        # 1 query per unique company (fallback for employees without a direct holiday list)
        companies_without_list = {
            row.company for row in emp_data if not row.holiday_list and row.company
        }
        company_holiday_map = {
            company: frappe.db.get_value("Company", company, "default_holiday_list")
            for company in companies_without_list
        }

        for row in emp_data:
            holiday_list = row.holiday_list or company_holiday_map.get(row.company)
            if holiday_list and holiday_list in holiday_lists_today:
                on_holiday.add(row.name)

    return on_leave | on_holiday


def time_diff_in_minutes(string_end_date, string_start_date):
    return time_diff(string_end_date, string_start_date).total_seconds() / 60


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
        "Employee", filters=default_shift_filters, pluck="name"
    )

    assigned_employees.extend(default_shift_employees)

    final_employees = frappe.get_all(
        "Employee",
        filters={"name": ["in", assigned_employees], "status": "Active"},
        fields=["name as employee", "user_id", "employee_name"],
    )

    return final_employees
