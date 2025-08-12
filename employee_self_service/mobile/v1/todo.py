import json
import frappe
from frappe.utils import today
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
)
from .task import fetch_user

TODO_FIELDS = [
    "name",
    "owner",
    "status",
    "priority",
    "date",
    "description",
    "reference_type",
    "reference_name",
    "allocated_to",
    "assigned_by",
    "_assign",
]
TODO_ERR = {
    "id_required": "ToDo ID is required",
    "not_found": "ToDo not found",
    "unauthorized": "You are not authorized to access this ToDo",
}


def validate_todo_access(todo):
    user = frappe.session.user
    if not todo:
        frappe.throw(TODO_ERR["not_found"])
    if not (
        todo.get("allocated_to") == user
        or todo.get("owner") == user
        or user in json.loads(todo.get("_assign") or "[]")
    ):
        frappe.throw(TODO_ERR["unauthorized"])


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_todo_list(view_type="all", start=0, page_length=10, filters=None):
    try:
        user = frappe.session.user
        base_filters = []
        filters = filters or []

        if view_type == "today":
            base_filters = [
                ["date", "=", today()],
                ["status", "!=", "Closed"],
            ]
        elif view_type == "all":
            base_filters = [
                ["status", "!=", "Closed"],
            ]
        elif view_type == "created_by_me":
            base_filters = [["owner", "=", user]]
        else:
            return gen_response(400, "Invalid view type")

        todos = frappe.get_all(
            "ToDo",
            filters=(
                filters + base_filters + [["allocated_to", "=", user]]
                if view_type != "created_by_me"
                else base_filters + filters
            ),
            fields=TODO_FIELDS,
            start=start,
            page_length=page_length,
            order_by="modified desc",
        )

        final = todos

        # Add assigned ToDos from _assign JSON (only for "today" and "all")
        if view_type in ("all", "today"):
            assigned_todos = frappe.get_all(
                "ToDo",
                filters=[
                    ["_assign", "like", f'%"{user}"%'],
                    ["status", "!=", "Closed"],
                ],
                fields=TODO_FIELDS,
            )
            # Deduplicate using name
            seen = {todo["name"] for todo in todos}
            for todo in assigned_todos:
                if todo["name"] not in seen:
                    final.append(todo)
                    seen.add(todo["name"])

        for f in final:
            f["assigned_by"] = fetch_user(f.get("assigned_by"))
            f["allocated_to"] = fetch_user(f.get("allocated_to"))

        return gen_response(200, "ToDo list fetched", final)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_todo_by_id(todo_id=None):
    try:
        if not todo_id:
            return gen_response(500, TODO_ERR["id_required"])
        todo = frappe.get_doc("ToDo", todo_id).as_dict()
        todo["assigned_by"] = fetch_user(todo.get("assigned_by"))
        todo["allocated_to"] = fetch_user(todo.get("allocated_to"))
        if not todo:
            return gen_response(404, TODO_ERR["not_found"])
        validate_todo_access(todo)
        return gen_response(200, "ToDo fetched", todo)
    except frappe.PermissionError:
        return gen_response(403, TODO_ERR["unauthorized"])
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def create_todo(**kwargs):
    try:
        data = frappe._dict(kwargs)
        todo = frappe.get_doc({"doctype": "ToDo"})
        todo.update(data)
        todo.owner = frappe.session.user
        todo.insert()
        return gen_response(200, "ToDo created successfully", {"name": todo.name})
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_todo(**kwargs):
    try:
        data = frappe._dict(kwargs)
        if not data.get("name"):
            return gen_response(500, TODO_ERR["id_required"])
        todo = frappe.get_doc("ToDo", data.name)
        validate_todo_access(todo)
        todo.update(data)
        todo.save()
        return gen_response(200, "ToDo updated successfully")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def update_todo_status(name=None, status=None):
    try:
        if not name:
            return gen_response(500, TODO_ERR["id_required"])
        if not status:
            return gen_response(500, "New status is required")
        todo = frappe.get_doc("ToDo", name)
        validate_todo_access(todo)
        if todo.status == status:
            return gen_response(200, "Status already up to date")
        todo.status = status
        todo.save()
        return gen_response(200, "Status updated successfully")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_todo_status_list():
    try:
        meta = frappe.get_meta("ToDo")
        options = []
        for df in meta.fields:
            if df.fieldname == "status" and df.fieldtype == "Select" and df.options:
                options = [
                    {"name": opt.strip()}
                    for opt in df.options.split("\n")
                    if opt.strip()
                ]
                break
        return gen_response(200, "ToDo Status List fetched successfully.", options)
    except frappe.PermissionError:
        return gen_response(403, "Not permitted to list options.")
    except Exception as e:
        return exception_handler(e)
