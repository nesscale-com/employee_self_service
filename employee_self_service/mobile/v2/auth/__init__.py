import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.twofactor import (
    authenticate_for_2factor,
    confirm_otp_token,
    should_run_2fa,
)
from frappe.utils import *
from employee_self_service.mobile.v1.auth.utils import *


@frappe.whitelist(allow_guest=True)
def login(usr, pwd, unique_id=None):
    try:
        login_manager = LoginManager()
        login_manager.authenticate(usr, pwd)
        validate_employee(login_manager.user)
        emp_data = get_employee_by_user(login_manager.user, fields=["name", "gender"])

        # Check if Two Factor Authentication is required for this user
        if should_run_2fa(login_manager.user):
            # Generate OTP and send it via the configured method (SMS / Email / OTP App)
            authenticate_for_2factor(login_manager.user)
            tmp_id = frappe.local.response.get("tmp_id")
            verification = frappe.local.response.get("verification")

            # Cache unique_id (device token) so it can be used after OTP verification
            if tmp_id and unique_id:
                frappe.cache.set(tmp_id + "_ess_unique_id", unique_id)
                frappe.cache.expire(tmp_id + "_ess_unique_id", 300)

            return gen_response(
                200,
                "Two factor authentication required",
                {
                    "two_factor_required": True,
                    "tmp_id": tmp_id,
                    "verification": verification,
                },
            )

        # Register device (throws exception if device is not valid)
        if unique_id:
            if not register_device(emp_data.get("name"), unique_id):
                return
        login_manager.post_login()
        if frappe.response["message"] == "Logged In":
            frappe.response["user"] = login_manager.user
            frappe.response["key_details"] = generate_key(login_manager.user)
            frappe.response["employee_id"] = emp_data.get("name")
            frappe.response["gender"] = emp_data.get("gender")
        gen_response(200, frappe.response["message"])
    except frappe.AuthenticationError:
        gen_response(500, frappe.response["message"])
    except frappe.SecurityException:
        gen_response(401, frappe.response["message"])
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist(allow_guest=True)
def verify_2fa_otp(tmp_id, otp):
    """
    Verify the OTP submitted by the user during Two Factor Authentication.

    Called after the initial `login` API returns a 202 with two_factor_required=True.
    On success, returns the same response as a normal successful login.

    Args:
        tmp_id (str): Temporary session identifier returned by the login API.
        otp   (str): One-time password entered by the user.
    """
    try:
        # Retrieve the username that was cached during the initial login step
        user = frappe.safe_decode(frappe.cache.get(tmp_id + "_usr"))
        if not user:
            return gen_response(401, "Login session has expired. Please login again.")

        # Build a minimal LoginManager so confirm_otp_token can track attempts
        login_manager = LoginManager()
        login_manager.user = user

        # Verify the OTP against the cached token / TOTP secret
        if not confirm_otp_token(login_manager, otp=str(otp), tmp_id=tmp_id):
            return gen_response(401, "Incorrect verification code. Please try again.")

        # OTP is valid – ensure the user is still linked to an Employee record
        validate_employee(user)
        emp_data = get_employee_by_user(user, fields=["name", "gender"])

        # Restore the unique_id (device token) that was cached during initial login
        unique_id = (
            frappe.safe_decode(frappe.cache.get(tmp_id + "_ess_unique_id")) or None
        )
        if unique_id:
            if not register_device(emp_data.get("name"), unique_id):
                return

        # Complete the login session
        login_manager.post_login()

        if frappe.response.get("message") == "Logged In":
            frappe.response["user"] = user
            frappe.response["key_details"] = generate_key(user)
            frappe.response["employee_id"] = emp_data.get("name")
            frappe.response["gender"] = emp_data.get("gender")

        gen_response(200, frappe.response.get("message", "Logged In"))
    except frappe.AuthenticationError:
        gen_response(500, frappe.response.get("message", "Authentication failed"))
    except frappe.SecurityException:
        gen_response(401, frappe.response.get("message", "Security error"))
    except Exception as e:
        return exception_handler(e)


@frappe.whitelist()
def change_password(data):
    try:
        from frappe.utils.password import check_password, update_password

        user = frappe.session.user
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        check_password(user, current_password)
        update_password(user, new_password)
        return gen_response(200, "Password updated")
    except frappe.AuthenticationError:
        return gen_response(500, "Incorrect current password")
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
@ess_validate(methods=["POST"])
def employee_device_info(**kwargs):
    try:
        data = kwargs
        existing_token = frappe.db.get_value(
            "Employee Device Info",
            filters={"user": frappe.session.user},
            fieldname="name",
        )
        if frappe.db.exists("Employee Device Info", existing_token):
            token = frappe.get_doc("Employee Device Info", existing_token)
            token.platform = data.get("platform")
            token.os_version = data.get("os_version")
            token.device_name = data.get("device_name")
            token.app_version = data.get("app_version")
            token.token = data.get("token")
            token.save(ignore_permissions=True)
        else:
            token = frappe.get_doc(
                doctype="Employee Device Info",
                platform=data.get("platform"),
                os_version=data.get("os_version"),
                device_name=data.get("device_name"),
                app_version=data.get("app_version"),
                token=data.get("token"),
                user=frappe.session.user,
            ).insert(ignore_permissions=True)

        emp_data = get_employee_by_user(frappe.session.user)
        existing_registration = frappe.db.exists(
            "Employee Device Registration", {"employee": emp_data.get("name")}
        )
        if not existing_registration and data.get("unique_id"):
            # Register the device if not exists
            doc = frappe.new_doc("Employee Device Registration")
            doc.employee = emp_data.get("name")
            doc.unique_id = data.get("unique_id")
            doc.insert(ignore_permissions=True)
        return gen_response(200, "Device information saved successfully!")
    except Exception as e:
        return exception_handler(e)
