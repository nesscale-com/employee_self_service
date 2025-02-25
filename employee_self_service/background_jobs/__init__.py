import frappe
from frappe.utils import today,add_days,cint
from employee_self_service.utils import is_holiday,get_employees_having_an_event_today,notification_log

def process_daily_ess_jobs():
	close_ess_poll()
	on_holiday_event()
	send_notification_on_event()


def close_ess_poll():
	try:
		filters = [
			["poll_end_date","=",add_days(today(),-1)],
			["post_type","=","Poll"]
		]
		ess_polls = frappe.get_all("ESS Post",filters=filters,fields=["name"])
		for row in ess_polls:
			poll_doc = frappe.get_doc("ESS Post",row.name)
			poll_doc.poll_closed = 1
			poll_doc.save(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(title="Close Poll Daily Job",message=frappe.get_traceback())

def on_holiday_event():
	try:
		enable_holiday_notification = frappe.db.get_value("ESS Notification Settings","ESS Notification Settings","enable_holiday_notification")
		if not cint(enable_holiday_notification) == 1:
			return 
		employees = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "user_id"]
		)

		user_device_info = {
			row.user_id: frappe.db.get_value("Employee Device Info", row.user_id, "token")
			for row in employees if row.user_id
		}
		for row in employees:
			if row.user_id:
				holiday,description = is_holiday(row.name, today(), only_non_weekly=True, with_description=True)
				if holiday:
					user_token = user_device_info.get(row.user_id)
					if user_token:
						notification_log(
							"Holiday",
							"Holiday List",
							frappe.utils.strip_html(description[0]),
							"Today is a holiday!",
							row.user_id,
							user_token
						)
	except Exception as e:
		frappe.log_error(title="daily job for the holiday",message=frappe.get_traceback())

def send_notification_on_event():
	try:
		enable_birthday_anniversary_notification = frappe.db.get_value("ESS Notification Settings","ESS Notification Settings","enable_birthday_anniversary_notification")
		if not cint(enable_birthday_anniversary_notification) == 1:
			return 
		birthday_events = get_employees_having_an_event_today("birthday", date=today())
		for event in birthday_events:
			user_token = frappe.db.get_value("Employee Device Info", event.user_id, "token")
			if user_token:
				template_doc = frappe.get_doc("ESS Notification Template","Birthday Notification")
				subject = frappe.render_template(template_doc.get("notification_title"),{"employee_name": event.name})
				message = template_doc.get("notification_message")
				notification_log(
					"Birthday",
					"Employee",
					subject,
					message,
					event.user_id,
					user_token
				)

		anniversary_events = get_employees_having_an_event_today(
			"work_anniversary", date=today()
		)
		for event in anniversary_events:
			user_token = frappe.db.get_value("Employee Device Info", event.user_id, "token")
			if user_token:
				template_doc = frappe.get_doc("ESS Notification Template","Work Anniversary")
				subject = frappe.render_template(template_doc.get("notification_title"),{"employee_name": event.name})
				message = template_doc.get("notification_message")
				notification_log(
					"Work Anniversary",
					"Employee",
					subject,
					message,
					event.user_id,
					user_token
				)
	except Exception as e:
		frappe.log_error(title="daily job for the event",message=frappe.get_traceback())