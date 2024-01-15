import frappe
import json
from frappe import _
from frappe.utils import pretty_date, getdate
from frappe.utils.data import now_datetime
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    remove_default_fields,
)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def ess_post(**data):
    try:
        if data.get("name"):
            post_doc = frappe.get_doc("ESS Post", data.get("name"))
        else:
            post_doc = frappe.new_doc("ESS Post")
            post_doc.user = frappe.session.user
            employee = get_employee_by_user(frappe.session.user)
            post_doc.employee = employee.get("name") if employee else ""
            post_doc.post_datetime = now_datetime()
        post_doc.update(data)
        post_doc.save(ignore_permissions=True)
        return gen_response(200, "Post updated successfully")
    except Exception as e:
        return exception_handler(e)


def get_ess_post(post_name):
    post_details = json.loads(frappe.get_doc("ESS Post", post_name).as_json())
    post_details = remove_default_fields(post_details)
    # post_details["comments"] = get_comments(
    #     post.get("name"), limit=2, internal=True
    # )
    post_details["comments_count"] = frappe.db.count(
        "Comment",
        {
            "reference_doctype": "ESS Post",
            "reference_name": post_name,
            "comment_type": "Comment",
        },
    )
    if post_details.get("_liked_by"):
        post_details["likes_count"] = len(json.loads(post_details["_liked_by"]))
        likes_list = json.loads(post_details["_liked_by"])
        if frappe.session.user in likes_list:
            post_details["liked_by_me"] = True
        else:
            post_details["liked_by_me"] = False

        post_details["_liked_by"] = frappe.get_all(
            "User",
            filters=[["name", "in", likes_list]],
            fields=["name", "full_name", "user_image"],
        )

    else:
        post_details["likes_count"] = 0
        post_details["liked_by_me"] = False
    if post_details.get("post_type") == "Poll":
        post_details["my_vote"] = frappe.db.get_value(
            "ESS Post Poll Log",
            {"user": frappe.session.user, "parent": post_details.get("name")},
            "answer",
        )
        post_details["total_vote"] = len(post_details.get("ess_post_poll_log"))
        
    if frappe.session.user != post_details.get('user'):
        del post_details["ess_post_poll_log"]
    else:
        for poll_log in post_details["ess_post_poll_log"]:
            remove_default_fields(poll_log)
        
    return post_details


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_feed(my_post=False, start=0, page_length=10):
    try:
        filters = []
        if my_post:
            filters.append(["user", "=", frappe.session.user])
        else:
            filters.append(["publish", "=", 1])
        posts = frappe.get_all(
            "ESS Post",
            filters=filters,
            fields=["name"],
            start=start,
            page_length=page_length,
            order_by="post_datetime desc",
        )
        feed_details = []
        for post in posts:
            post_details = get_ess_post(post_name=post.name)
            feed_details.append(post_details)
        return gen_response(200, "post details get successfully", feed_details)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def delete_post(post_id):
    try:
        if frappe.db.exists("ESS Post", {"user": frappe.session.user, "name": post_id}):
            frappe.delete_doc("ESS Post", post_id)
            return gen_response(200, "Post deleted successfully")
        else:
            return gen_response(500, "Invalid Post")
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def add_comment(post_id, content=None):
    try:
        from frappe.desk.form.utils import add_comment

        comment_by = frappe.db.get_value(
            "User", frappe.session.user, "full_name", as_dict=1
        )

        add_comment(
            reference_doctype="ESS Post",
            reference_name=post_id,
            content=content,
            comment_email=frappe.session.user,
            comment_by=comment_by.get("full_name"),
        )
        return gen_response(200, "Comment added successfully")

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_comments(post_id=None, start=0, page_length=10, limit=20, internal=False):
    """
    reference_doctype: doctype
    reference_name: docname
    """
    try:
        filters = [
            ["Comment", "reference_doctype", "=", "ESS Post"],
            ["Comment", "reference_name", "=", post_id],
            ["Comment", "comment_type", "=", "Comment"],
        ]
        comments = frappe.get_all(
            "Comment",
            filters=filters,
            fields=[
                "content",
                "comment_by",
                "creation",
                "comment_email",
            ],
            start=start,
            page_length=page_length,
            limit=limit,
            order_by="modified desc",
        )

        for comment in comments:
            user_image = frappe.get_value(
                "User", comment.comment_email, "user_image", cache=True
            )
            comment["user_image"] = user_image
            comment["commented"] = pretty_date(comment["creation"])
            comment["creation"] = comment["creation"].strftime("%I:%M %p")
        if internal:
            return comments
        return gen_response(200, "Comments get successfully", comments)

    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def post_like_toggle(post_id, like=False):
    try:
        from frappe.desk.like import toggle_like

        if like:
            toggle_like(doctype="ESS Post", name=post_id, add="Yes")
        else:
            toggle_like(doctype="ESS Post", name=post_id, add="No")

        count = len(json.loads(frappe.db.get_value("ESS Post", post_id, "_liked_by")))
        post_data = get_ess_post(post_name=post_id)
        return gen_response(200, "Like updated", post_data)
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
@ess_validate(methods=["POST"])
def poll_user_answer(post_id, answer):
    try:
        if frappe.get_value("ESS Post", post_id, "poll_end_date") < getdate():
            return gen_response("403", "Poll is ended")
        poll_answer = frappe.db.get_value(
            "ESS Post Poll Log",
            {"user": frappe.session.user, "parent": post_id},
            "name",
        )
        if poll_answer:
            frappe.db.set_value("ESS Post Poll Log", poll_answer, "answer", answer)
            post_doc = frappe.get_doc("ESS Post", post_id)
            post_doc.save(ignore_permissions=True)
        else:
            post_doc = frappe.get_doc("ESS Post", post_id)
            post_doc.append(
                "ess_post_poll_log", dict(user=frappe.session.user, answer=answer)
            )
            post_doc.save(ignore_permissions=True)
        post_data = get_ess_post(post_name=post_id)
        return gen_response(200, "Poll answer added", post_data)
    except Exception as e:
        return exception_handler(e)
