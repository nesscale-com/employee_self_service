import frappe
from employee_self_service.mobile.v1.notification.utils import *


@frappe.whitelist()
@ess_validate(methods=["GET"])
def notification_list_old():
    try:
        single_filters = [
            ["Push Notification", "user", "=", frappe.session.user],
            ["Push Notification", "send_for", "=", "Single User"],
        ]
        notification = frappe.get_all(
            "Push Notification",
            filters=single_filters,
            fields=["title", "message", "creation"],
        )
        multiple_filters = [
            ["Notification User", "user", "=", frappe.session.user],
            ["Push Notification", "send_for", "=", "Multiple User"],
        ]
        multiple_notification = frappe.get_all(
            "Push Notification",
            filters=multiple_filters,
            fields=["title", "message"],
        )
        notification.extend(multiple_notification)
        all_filters = [["Push Notification", "send_for", "=", "All User"]]

        all_notification = frappe.get_all(
            "Push Notification",
            filters=all_filters,
            fields=["title", "message"],
        )

        notification.extend(all_notification)

        for notified in notification:
            notified["creation"] = pretty_date(notified.get("creation"))
            notified["user_image"] = frappe.get_value(
                "User", frappe.session.user, "user_image"
            )
        return gen_response(200, "Notification list get successfully", notification)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def notification_list(start=0, page_length=20):
    try:
        filters = [
            ["ESS Notification Log", "recipient", "=", frappe.session.user],
        ]
        # ["ESS Notification Log", "read", "=", 0],
        notifications = frappe.get_all(
            "ESS Notification Log",
            filters=filters,
            fields=[
                "name",
                "subject as 'title'",
                "message",
                "creation",
                "reference_document",
                "reference_name",
                "other_info",
                "read",
            ],
            start=start,
            page_length=page_length,
        )
        user_image = frappe.get_value("User", frappe.session.user, "user_image")
        for notification in notifications:
            notification["name"] = cstr(notification.get("name"))
            notification["navigate_route"] = get_mobile_app_route(
                notification.get("reference_document"),
                notification.get("reference_name"),
            )
            notification["creation"] = pretty_date(notification.get("creation"))
            notification["user_image"] = user_image
        return gen_response(200, "Notification list get successfully", notifications)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def mark_read_notification(name=None):
    try:
        if not name:
            frappe.db.set_value(
                "ESS Notification Log", {"recipient": frappe.session.user}, "read", 1
            )
        else:
            frappe.db.set_value("ESS Notification Log", {"name": name}, "read", 1)
        return gen_response(200, "Notification mark read successfully")
    except Exception as e:
        return exception_handler(e)
