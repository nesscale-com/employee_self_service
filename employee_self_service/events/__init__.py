import frappe
import requests
from frappe import _
from frappe.utils import cint

from employee_self_service.utils import notification_log


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
    except Exception:
        frappe.log_error(
            title="After Insert Comment ESS Notification Error",
            message=frappe.get_traceback(),
        )


def set_location_address(doc, methods):
    try:
        if doc.location:
            doc.log_location = get_address_from_location(doc.location)
            doc.save()
    except Exception:
        frappe.log_error(
            title="Failed to fetch location address", message=frappe.get_traceback()
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
