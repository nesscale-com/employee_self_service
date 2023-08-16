# Copyright (c) 2022, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
import pyfcm
from frappe.model.document import Document
from pyfcm import FCMNotification
import json
import datetime


class PushNotification(Document):
    def after_insert(self):
        server_key = frappe.db.get_single_value(
            "Employee Self Service Settings", "firebase_server_key"
        )
        if not server_key:
            return
        if self.send_for == "Single User":
            token = frappe.db.get_value(
                "Employee Device Info",
                filters={"user": self.user},
                fieldname="token",
            )
            if token:
                self.response = json.dumps(
                    send_single_notification(
                        token,
                        self.title,
                        self.message,
                        self.user,
                        self.notification_type,
                    )
                )
                self.save()

        elif self.send_for == "Multiple User":
            users = [nu.user for nu in self.users]
            registration_ids = frappe.db.get_list(
                "Employee Device Info",
                filters=[
                    ["Employee Device Info", "user", "in", users],
                    ["Employee Device Info", "token", "is", "set"],
                ],
                fields=["token"],
            )
            if registration_ids:
                registration_ids = [token["token"] for token in registration_ids]
                self.response = json.dumps(
                    send_multiple_notification(
                        registration_ids,
                        users,
                        self.title,
                        self.message,
                        self.notification_type,
                    )
                )
                self.save()
        elif self.send_for == "All User":
            registration_ids = frappe.db.get_list(
                "Employee Device Info",
                filters=[["Employee Device Info", "token", "is", "set"]],
                fields=["token"],
            )
            if registration_ids:
                registration_ids = [token["token"] for token in registration_ids]
                self.response = json.dumps(
                    send_multiple_notification(
                        registration_ids,
                        self.title,
                        self.message,
                        self.notification_type,
                    )
                )
                self.save()


@frappe.whitelist()
def send_single_notification(
    registration_id,
    title=None,
    message=None,
    user=None,
    notification_type=None,
):
    server_key = frappe.db.get_single_value(
        "Employee Self Service Settings", "firebase_server_key"
    )

    push_service = FCMNotification(api_key=server_key)
    # push_service = FCMNotification(
    #     api_key="AAAAPcJ19TQ:APA91bH0IMYIyGdAAhH0SCEoXHr1gS4jjeaZgCsIcjr5uF5adQqiPG-QARbOx6XS4XOB3W3Km65xJUBo1W6jg8uLYcuHKSMcu-U7QurQLuEEOXHAu9eH9eLYg0RDtNOqYwEAIoOwBHqF"
    # )

    registration_id = registration_id
    message_title = title
    message_body = message

    data_message = {
        "notification_type": notification_type,
    }

    return push_service.notify_single_device(
        registration_id=registration_id,
        message_title=message_title,
        message_body=message_body,
        data_message=data_message,
    )


@frappe.whitelist()
def send_multiple_notification(
    registration_ids, users=None, title=None, message=None, notification_type=None
):
    server_key = frappe.db.get_single_value(
        "Employee Self Service Settings", "firebase_server_key"
    )
    push_service = FCMNotification(api_key=server_key)
    # push_service = FCMNotification(
    #     api_key="AAAAPcJ19TQ:APA91bH0IMYIyGdAAhH0SCEoXHr1gS4jjeaZgCsIcjr5uF5adQqiPG-QARbOx6XS4XOB3W3Km65xJUBo1W6jg8uLYcuHKSMcu-U7QurQLuEEOXHAu9eH9eLYg0RDtNOqYwEAIoOwBHqF"
    # )

    registration_ids = registration_ids
    message_title = title
    message_body = message
    data_message = {"notification_type": notification_type}
    return push_service.notify_multiple_devices(
        registration_ids=registration_ids,
        message_title=message_title,
        message_body=message_body,
        data_message=data_message,
    )


def create_push_notification(title, message, send_for, notification_type, user=None):
    push_notification_doc = frappe.new_doc("Push Notification")
    push_notification_doc.title = title
    push_notification_doc.message = message
    push_notification_doc.send_for = send_for
    push_notification_doc.user = user
    push_notification_doc.notification_type = notification_type
    push_notification_doc.save(ignore_permissions=True)
