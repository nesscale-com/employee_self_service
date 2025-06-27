import frappe
from frappe import _
from frappe.sessions import clear_sessions
from .auth_utils import *


class Auth:
    def __init__(self) -> None:
        self.user = frappe.session.user

    def login(self,usr, pwd, unique_id=None):
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(usr, pwd)
        validate_employee(login_manager.user)
        emp_data = get_employee_by_user(login_manager.user, fields=["name", "gender"])
        # Register device (throws exception if device is not valid)
        if unique_id:
            if not register_device(emp_data.get("name"), unique_id):
                return
        login_manager.post_login()
        if frappe.response["message"] == "Logged In":

            frappe.response["user"] = self.user
            frappe.response["key_details"] = self.generate_key(self.user)
            frappe.response["employee_id"] = emp_data.get("name")
            frappe.response["gender"] = emp_data.get("gender")

    def generate_key(self,user):
        user_details = frappe.get_doc("User", user)
        api_secret = api_key = ""
        if not user_details.api_key and not user_details.api_secret:
            api_secret = frappe.generate_hash(length=15)
            # if api key is not set generate api key
            api_key = frappe.generate_hash(length=15)
            user_details.api_key = api_key
            user_details.api_secret = api_secret
            user_details.save(ignore_permissions=True)
        else:
            api_secret = user_details.get_password("api_secret")
            api_key = user_details.get("api_key")
        return {"api_secret": api_secret, "api_key": api_key}
    
    def register_device(employee, unique_id):
        # check if device registration exists for this employee
        # if not enter the given number and create registration
        # if exists than validate the given number with existing number
        # if number mataches than allow login
        # else through frappe exceptions
        ess_settings = get_ess_settings()
        if not ess_settings.get("enable_device_restrictions"):
            return True

        existing_registration = frappe.db.exists(
            "Employee Device Registration", {"employee": employee}
        )

        if not existing_registration:
            # Register the device if not exists
            doc = frappe.new_doc("Employee Device Registration")
            doc.employee = employee
            doc.unique_id = unique_id
            doc.insert(ignore_permissions=True)
        else:
            # Fetch the existing device_id to compare
            registered_device_id = frappe.db.get_value(
                "Employee Device Registration", existing_registration, "unique_id"
            )
            if registered_device_id != unique_id:
                gen_response(500, "Device not recognized. Please contact admin.")
                return False
        return True