import frappe
import requests

from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    generate_key,
    ess_validate,
    get_employee_by_user,
    validate_employee_data,
    get_ess_settings,
    get_global_defaults,
    exception_handler,
    convert_timezone,
    get_system_timezone,
)

@frappe.whitelist(allow_guest=True)
def azure_login(access_token):
    """
    Validate Azure AD access token and log in or create the user in Frappe.
    """
    # Azure endpoint to validate the token
    url = "https://graph.microsoft.com/v1.0/me"

    # Validate the token with Azure
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        email = user_info.get("mail") or user_info.get("userPrincipalName")

        if not email:
            frappe.throw("Email not found in Azure token")

        # Check if user exists in Frappe
        user = frappe.db.exists("User", email)
        if not user:
            # Create a new user if it doesn't exist
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": user_info.get("displayName", "Unknown User"),
                "enabled": 1,
                "user_type": "Website User"
            }).insert(ignore_permissions=True)

        # Log in the user and return session
        frappe.local.login_manager.user = email
        frappe.local.login_manager.post_login()

        if frappe.response["message"] == "Logged In":
            emp_data = get_employee_by_user(frappe.local.login_manager.user)
            frappe.response["user"] = frappe.local.login_manager.user
            frappe.response["key_details"] = generate_key(frappe.local.login_manager.user)
            frappe.response["employee_id"] = emp_data.get("name")
            gen_response(200, frappe.response["message"])
        else:
            gen_response(500, frappe.response["message"])
    else:
        # frappe.throw(f"Azure token validation failed: {response.content.decode()}")
        gen_response(500, "Invalid Login Credentials")



@frappe.whitelist(allow_guest=True)
def get_office360_details():
    return {
        "tenant_id": "15c454c4-a26d-491f-9d25-549d62f4e2b4",
        "client_id": "4fe26052-cb2e-4b90-958e-b50e4be40fbc",
    }