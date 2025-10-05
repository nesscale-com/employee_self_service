import frappe
import requests
from frappe.utils import cint, get_datetime, today
from employee_self_service.utils import notification_log
from frappe import _
from employee_self_service.mobile.v1.ess import get_last_log_type
from datetime import timedelta


def after_insert_comment(doc, method=None):
    try:
        if doc.reference_doctype != "ESS Post":
            return

        template_name = None
        action_type = None
        notification_settings = frappe.get_doc(
            "ESS Notification Settings", "ESS Notification Settings"
        )
        if (
            not cint(notification_settings.get("enable_like_and_comment_notification"))
            == 1
        ):
            return
        if doc.comment_type == "Like":
            template_name = "Notification Like"
            action_type = "ESS Post Like"
        elif doc.comment_type == "Comment":
            template_name = "Post Comment"
            action_type = "ESS Post Comment"

        if not template_name:
            return

        # Fetch template details once
        template_doc = frappe.get_doc("ESS Notification Template", template_name)

        # Fetch user details once
        user_details = frappe.db.get_value(
            doc.reference_doctype, doc.reference_name, ["user"], as_dict=True
        )
        if not user_details or not user_details.get("user"):
            return

        user = user_details["user"]
        user_name = frappe.db.get_value("User", doc.comment_email, "full_name")

        # Render notification message
        message = frappe.render_template(
            template_doc.notification_message, {"user_name": user_name}
        )
        subject = template_doc.get("notification_title")

        # Get user token once
        user_token = frappe.db.get_value("Employee Device Info", user, "token")
        if user_token:
            # Send notification
            notification_log(
                action_type, doc.reference_doctype, subject, message, user, user_token
            )
    except Exception as e:
        frappe.log_error(
            title="After Insert Comment ESS Notification Error",
            message=frappe.get_traceback(),
        )


def set_location_address(doc, methods):
    try:
        if doc.location:
            doc.log_location = get_address_from_location(doc.location)
            doc.save()
    except Exception as e:
        frappe.log_error(
            title="Failed to fetch location address", message=frappe.get_traceback()
        )


def validate_consecutive_log_type(doc, method=None):
    """
    Validate that consecutive Employee Checkins don't have the same log_type for the same employee.
    This prevents employees from checking in twice in a row or checking out twice in a row.
    """
    if not doc.employee or not doc.log_type:
        return

    shift_policy = frappe.db.get_value(
        "Employee", doc.employee, "custom_pollen_shift_policy"
    )
    # Validate check-in window time first
    if doc.log_type == "IN":
        validate_checkin_window_time(doc, shift_policy)

    last_log_details = get_last_log_type(doc.employee, shift_policy)

    if last_log_details:
        last_log_type = last_log_details.get("log_type")

        # If the last check-in has the same log_type as the current one, throw an error
        if last_log_type == doc.log_type:
            if doc.log_type == "IN":
                frappe.throw(
                    _(
                        "Employee {0} already has a Check-In entry as their last record. Please Check-Out first before making another Check-In."
                    ).format(doc.employee)
                )
            elif doc.log_type == "OUT":
                frappe.throw(
                    _(
                        "Employee {0} already has a Check-Out entry as their last record. Please Check-In first before making another Check-Out."
                    ).format(doc.employee)
                )
            else:
                frappe.throw(
                    _(
                        "Employee {0} already has a {1} entry as their last record. Cannot make consecutive entries of the same type."
                    ).format(doc.employee, doc.log_type)
                )


def validate_checkin_window_time(doc, shift_policy_name=None):
    """
    Validate that the employee is checking in within the allowed window time.
    Users should only be able to check in within the early check-in window
    (e.g., 30 minutes before shift start) as defined in their shift policy.
    """
    if not doc.employee:
        return

    if not shift_policy_name:
        # If no shift policy is assigned, skip this validation
        return

    # Get shift policy details
    try:
        shift_policy = frappe.get_doc("Pollen Shift Policy", shift_policy_name)
    except frappe.DoesNotExistError:
        # If shift policy doesn't exist, skip validation
        return

    # Get the current date and shift start time
    current_date = today()
    shift_start_time = shift_policy.start_time
    early_checkin_window_minutes = float(
        shift_policy.early_checkin_window_minutes or 120
    )

    # Construct shift start datetime for today
    shift_start_datetime = get_datetime(f"{current_date} {shift_start_time}")

    # Calculate the earliest allowed check-in time
    earliest_checkin_time = shift_start_datetime - timedelta(
        minutes=early_checkin_window_minutes
    )

    # Get the current check-in time (or use current time if not specified)
    checkin_time = get_datetime(doc.time) if doc.time else get_datetime()

    # Validate that check-in is not too early
    if checkin_time < earliest_checkin_time:
        # Calculate how many minutes early the user is trying to check in
        minutes_too_early = (earliest_checkin_time - checkin_time).total_seconds() / 60

        frappe.throw(
            _(
                "You cannot check in before {0}. You are trying to check in {1} minutes too early. "
                "The earliest allowed check-in time is {2} minutes before shift start time ({3})."
            ).format(
                earliest_checkin_time.strftime("%I:%M %p"),
                int(minutes_too_early),
                int(early_checkin_window_minutes),
                shift_start_datetime.strftime("%I:%M %p"),
            )
        )


def get_address_from_location(location):
    """
    Fetch the address from latitude and longitude using OpenStreetMap's Nominatim API.

    :param location: A string in "latitude,longitude" format
    :return: Address as a string or an error message
    """

    # Validate input
    if not location or "," not in location:
        frappe.throw(_("Invalid location format. Use 'latitude,longitude'."))

    # Extract latitude and longitude from the string
    lat, lon = location.split(",")
    lat, lon = lat.strip(), lon.strip()

    # Construct the API request
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
    response = requests.get(url, headers={"User-Agent": "Frappe-App"})

    # Handle response
    if response.status_code == 200:
        data = response.json()
        address = data.get("display_name", "")
        return address
    else:
        frappe.throw(_("Error Fetching Address"))
