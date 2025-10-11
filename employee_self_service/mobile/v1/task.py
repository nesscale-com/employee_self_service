import json

import frappe
from frappe.utils import pretty_date, today

from employee_self_service.mobile.v1.api_utils import (
    ess_validate,
    exception_handler,
    gen_response,
)

TASK_FIELDS = ["_assign", "owner", "status"]
ERR = {
    "not_assigned": "Task is not assigned to any user",
    "unauthorized": "You are not authorized to update this task",
    "id_required": "Task ID is required",
    "progress_required": "Progress is required",
    "status_required": "New status is required",
    "already_updated": "Status is already up to date",
}


def validate_assign_task(task_data):
    if not task_data.get("_assign"):
        frappe.throw(ERR["not_assigned"])

    try:
        assigned_users = json.loads(task_data["_assign"])
    except Exception:
        assigned_users = []

    if (
        frappe.session.user not in assigned_users
        and frappe.session.user != task_data.get("owner")
    ):
        frappe.throw(ERR["unauthorized"])


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_task_status(task_id=None, new_status=None):
    try:
        if not task_id:
            return gen_response(500, ERR["id_required"])
        if not new_status:
            return gen_response(500, ERR["status_required"])

        task_data = frappe.db.get_value(
            "Task", {"name": task_id}, TASK_FIELDS, as_dict=True
        )
        if not task_data:
            return gen_response(404, "Task not found")

        validate_assign_task(task_data)

        if task_data.status == new_status:
            return gen_response(500, ERR["already_updated"])

        update_values = {"status": new_status}
        if new_status == "Completed":
            update_values.update(
                {"completed_by": frappe.session.user, "completed_on": today()}
            )

        frappe.db.set_value("Task", task_id, update_values)
        return gen_response(200, "Task status updated successfully")
    except frappe.PermissionError:
        return gen_response(403, ERR["unauthorized"])
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_task_progress(task_id=None, progress=None):
    try:
        if not task_id:
            return gen_response(500, ERR["id_required"])
        if progress is None:
            return gen_response(500, ERR["progress_required"])

        task_data = frappe.db.get_value(
            "Task", task_id, ["_assign", "owner"], as_dict=True
        )
        if not task_data:
            return gen_response(404, "Task not found")

        validate_assign_task(task_data)
        frappe.db.set_value("Task", task_id, "progress", progress)
        return gen_response(200, "Progress updated successfully")
    except frappe.PermissionError:
        return gen_response(403, ERR["unauthorized"])
    except Exception as e:
        return exception_handler(e)


def update_task_filters(filters, today_task):
    if isinstance(filters, str):
        filters = json.loads(filters)
    if today_task:
        filters.append(["Task", "exp_end_date", "=", today()])
    return filters


def fetch_user_details(emails):
    return (
        frappe.get_all(
            "User",
            filters={"email": ["in", emails]},
            fields=["name", "full_name", "full_name as user", "user_image"],
            order_by="creation asc",
        )
        if emails
        else []
    )


def fetch_project_map(project_ids):
    if not project_ids:
        return {}
    return {
        row.name: row.project_name
        for row in frappe.get_all(
            "Project",
            filters={"name": ["in", project_ids]},
            fields=["name", "project_name"],
        )
    }


def fetch_user(user_id):
    if not user_id:
        return None
    return frappe.db.get_value(
        "User",
        user_id,
        ["name", "full_name", "full_name as user", "user_image"],
        as_dict=True,
    )


def fetch_comments(task_id):
    comments = frappe.get_all(
        "Comment",
        filters={
            "reference_name": task_id,
            "comment_type": "Comment",
        },
        fields=[
            "content as comment",
            "comment_by",
            "reference_name",
            "creation",
            "comment_email",
        ],
    )
    for comment in comments:
        comment["commented"] = pretty_date(comment["creation"])
        comment["creation"] = comment["creation"].strftime("%I:%M %p")
        comment["user_image"] = frappe.db.get_value(
            "User", comment["comment_email"], "user_image", cache=True
        )
    return comments


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_list(start=0, page_length=10, filters=None, today_task=False):
    try:
        if not frappe.has_permission("Task", "read"):
            frappe.throw("Not permitted to read Task", frappe.PermissionError)

        filters = update_task_filters(filters, today_task)
        tasks = frappe.get_list(
            "Task",
            fields=[
                "name",
                "subject",
                "project",
                "priority",
                "status",
                "description",
                "exp_end_date",
                "_assign as assigned_to",
                "owner as assigned_by",
                "progress",
                "issue",
            ],
            filters=filters,
            start=start,
            page_length=page_length,
            order_by="modified desc",
        )

        project_map = fetch_project_map(
            {t["project"] for t in tasks if t.get("project")}
        )

        for task in tasks:
            if task.get("exp_end_date"):
                task["exp_end_date"] = task["exp_end_date"].strftime("%d %b %Y")
            task["project_name"] = project_map.get(task.get("project"))
            task["assigned_by"] = fetch_user(task.get("assigned_by"))
            task["comments"] = fetch_comments(task["name"])
            task["num_comments"] = len(task["comments"])

            try:
                emails = json.loads(task.get("assigned_to") or "[]")
            except Exception:
                emails = []

            task["assigned_to"] = fetch_user_details(emails)

        return gen_response(200, "Task list fetched successfully", tasks)

    except frappe.PermissionError:
        return gen_response(403, "Not permitted to read Task")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_list_dashboard():
    try:
        filters = [
            ["_assign", "like", f"%{frappe.session.user}%"],
            ["status", "!=", "Completed"],
        ]
        tasks = frappe.get_all(
            "Task",
            fields=[
                "name",
                "subject",
                "project",
                "priority",
                "status",
                "description",
                "exp_end_date",
                "_assign as assigned_to",
                "owner as assigned_by",
                "progress",
            ],
            filters=filters,
            limit=4,
        )

        project_map = fetch_project_map(
            {t["project"] for t in tasks if t.get("project")}
        )

        for task in tasks:
            if task["exp_end_date"]:
                task["exp_end_date"] = task["exp_end_date"].strftime("%d %b %Y")

            task["project_name"] = project_map.get(task.get("project"))
            task["assigned_by"] = fetch_user(task.get("assigned_by"))
            task["comments"] = fetch_comments(task["name"])
            task["num_comments"] = len(task["comments"])

            try:
                emails = json.loads(task.get("assigned_to") or "[]")
            except Exception:
                emails = []

            task["assigned_to"] = fetch_user_details(emails)

        return gen_response(200, "Task list fetched successfully", tasks)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_by_id(task_id=None):
    try:
        if not task_id:
            return gen_response(500, "task_id is required", [])

        task = frappe.db.get_value(
            "Task",
            {"name": task_id},
            [
                "name",
                "subject",
                "project",
                "priority",
                "status",
                "description",
                "exp_end_date",
                "expected_time",
                "actual_time",
                "_assign as assigned_to",
                "owner as assigned_by",
                "completed_by",
                "completed_on",
                "progress",
                "issue",
            ],
            as_dict=True,
        )
        if not task:
            return gen_response(404, "No task found", [])

        task["assigned_by"] = fetch_user(task.get("assigned_by"))
        task["completed_by"] = fetch_user(task.get("completed_by"))
        task["project_name"] = frappe.db.get_value(
            "Project", task.get("project"), "project_name"
        )

        try:
            emails = json.loads(task.get("assigned_to") or "[]")
        except Exception:
            emails = []

        task["assigned_to"] = (
            frappe.get_all(
                "User",
                filters={"email": ["in", emails]},
                fields=["name", "full_name as user", "full_name", "user_image"],
                order_by="creation asc",
            )
            if emails
            else []
        )

        task["comments"] = fetch_comments(task["name"])
        task["num_comments"] = len(task["comments"])

        return gen_response(200, "Task", task)

    except frappe.PermissionError:
        return gen_response(403, "Not permitted to read task")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_task(**kwargs):
    try:
        from frappe.desk.form import assign_to

        data = kwargs
        task_doc = frappe.get_doc(dict(doctype="Task"))
        task_doc.update(data)
        task_doc.insert()
        if data.get("assign_to"):
            assign_to.add(
                {
                    "assign_to": data.get("assign_to"),
                    "doctype": task_doc.doctype,
                    "name": task_doc.name,
                }
            )
        return gen_response(200, "Task has been created successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for create task")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_task(**kwargs):
    try:
        from frappe.desk.form import assign_to

        data = kwargs
        task_doc = frappe.get_doc("Task", data.get("name"))
        task_doc.update(data)
        task_doc.save()
        if data.get("assign_to"):
            assign_to.add(
                {
                    "assign_to": data.get("assign_to"),
                    "doctype": task_doc.doctype,
                    "name": task_doc.name,
                }
            )
        return gen_response(200, "Task has been updated successfully")
    except frappe.PermissionError:
        return gen_response(500, "Not permitted for update task")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_task_status_list():
    try:
        task_status = frappe.get_meta("Task").get_field("status").options or ""
        if task_status:
            task_status = task_status.split("\n")
        return gen_response(200, "Status get successfully", task_status)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_project_list():
    try:
        project_list = frappe.get_list("Project", ["name", "project_name"])
        return gen_response(200, "Project List getting Successfully", project_list)
    except frappe.PermissionError:
        return gen_response(500, "Not permitted read project")
    except Exception as e:
        return exception_handler(e)
