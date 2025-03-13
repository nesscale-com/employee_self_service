import frappe
import requests
import json
from frappe import enqueue
from frappe.utils import parse_val, cint
from employee_self_service.utils import notification_log

event_mapping = {
    "after_insert": "New",
    "on_update": "Save",
    "on_submit": "Submit",
    "before_cancel": "Cancel",
    "after_cancel": "Cancel",
    "days_after": "Days After",
    "days_before": "Days Before",
}


@frappe.whitelist()
def notification(doc, event):
    try:
        if frappe.db.exists("DocType", "ESS Notification"):
            notification_processing(doc, event)
    except Exception as e:
        frappe.log_error(
            title="ESS Notification Trigger Error", message=frappe.get_traceback()
        )


def get_user_tokens(notification_id, doc):
    """
    Fetch user tokens for push notifications based on the ESS Notification Recipient configuration.
    """
    to_users_data = []

    # Fetch recipients from the notification configuration
    recipients = frappe.get_all(
        "ESS Notification Recipient", filters={"parent": notification_id}, fields=["*"]
    )

    if not recipients:
        return to_users_data  # Return empty list if no recipients are defined

    user_emails = set()  # Use a set to avoid duplicate emails
    for recipient in recipients:
        # Fetch emails based on role
        if recipient.get("receiver_by_role"):
            role_users = frappe.db.sql(
                """
                SELECT u.email
                FROM `tabUser` u
                JOIN `tabHas Role` hr ON u.name = hr.parent
                WHERE hr.role = %s
                """,
                (recipient["receiver_by_role"],),
                as_dict=True,
            )
            user_emails.update([user["email"] for user in role_users])

        # Fetch email from document field
        if recipient.get("receiver_by_document_field"):
            data_field, child_field = _parse_receiver_by_document_field(
                recipient.receiver_by_document_field
            )
            if child_field:
                for d in doc.get(child_field):
                    email_id = d.get(data_field)
                    user_emails.add(email_id)
            # field from current doc
            else:
                user_field_email = doc.get(data_field)
                if user_field_email:
                    user_emails.add(user_field_email)

        # Fetch email from employee linked field
        if recipient.get("receiver_by_employee_field"):
            employee_id = doc.get(recipient["receiver_by_employee_field"])
            if employee_id:
                employee_user = frappe.db.get_value("Employee", employee_id, "user_id")
                if employee_user:
                    user_emails.add(employee_user)

        # Include all assignees if specified
        if cint(recipient.get("send_to_all_assignees")) == 1:
            assignees = doc.get("_assign")
            if assignees:
                user_emails.update(json.loads(assignees))

    if user_emails:
        # Fetch tokens from Employee Device Info based on collected user emails
        to_users_data = frappe.get_all(
            "Employee Device Info",
            filters={"name": ["in", list(user_emails)]},
            fields=["name", "token"],
        )

    return to_users_data


def _parse_receiver_by_document_field(s):
    fragments = s.split(",")
    # fields from child table or linked doctype
    if len(fragments) > 1:
        data_field, child_field = fragments
    else:
        data_field, child_field = fragments[0], None
    return data_field, child_field


def notification_processing(doc, event):
    if not doc.flags.in_insert:
        # value change is not applicable in insert
        event_mapping["on_change"] = "Value Change"
    event_type = event_mapping.get(event)
    if not event_type:
        return
    setting = frappe.get_doc(
        "Employee Self Service Settings", "Employee Self Service Settings"
    )
    if not setting.get("enable_ess_notification"):
        return
    notifications = frappe.get_all(
        "ESS Notification",
        filters={
            "enabled": 1,
            "event": event_type,
            "document_type": doc.doctype,
        },
        fields=[
            "name",
            "subject",
            "message",
            "condition",
            "document_type",
            "value_changed",
        ],
    )
    if not notifications:
        return
    recipients = []
    for notification in notifications:
        if notification["condition"]:
            condition_result = frappe.safe_eval(
                notification["condition"], None, {"doc": doc}
            )
            if not condition_result:
                continue
        if event_type == "Value Change" and not doc.is_new():
            if not frappe.db.has_column(doc.doctype, notification.value_changed):
                continue
            else:
                doc_before_save = doc.get_doc_before_save()
                field_value_before_save = (
                    doc_before_save.get(notification.value_changed)
                    if doc_before_save
                    else None
                )
                field_value_before_save = parse_val(field_value_before_save)
                if doc.get(notification.value_changed) == field_value_before_save:
                    # value not changed
                    continue
                else:
                    recipients = get_user_tokens(notification["name"], doc)
                    frappe.enqueue(
                        send_notification,
                        doc=doc,
                        notification=notification,
                        recipients=recipients,
                        queue="short",
                        timeout=1000,
                    )
        else:
            recipients = get_user_tokens(notification["name"], doc)
            frappe.enqueue(
                send_notification,
                doc=doc,
                notification=notification,
                recipients=recipients,
                queue="short",
                timeout=1000,
            )


def send_notification(doc, notification, recipients):
    subject = frappe.render_template(notification["subject"], {"doc": doc})
    message = frappe.render_template(notification["message"], {"doc": doc})
    other_info = ""
    document_type = doc.doctype
    document_name = doc.name
    if doc.doctype == "Notification Log":
        other_info = doc.type
        document_type = doc.document_type
        document_name = doc.document_name
    for user in recipients:
        notification_log(
            notification["name"],
            doc.doctype,
            subject,
            message,
            user.get("name"),
            user.get("token"),
            document_type,
            document_name,
            other_info,
        )
