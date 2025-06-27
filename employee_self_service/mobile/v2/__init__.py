import frappe
from employee_self_service.mobile.v2.modules.log import log
from pydantic import ValidationError
from bs4 import BeautifulSoup
from employee_self_service.mobile.v2.modules.rate_limiter import CustomRateLimiter
from employee_self_service.mobile.v2.endpoints_loader import get_combined_endpoints

# Get all API endpoints
endpoints = get_combined_endpoints()


def get_allow_guest(type: str):
	endpoint = endpoints.get(type)
	return endpoint.get("allow_guest", False) if endpoint else False

@frappe.whitelist(methods=["POST", "GET", "PUT", "DELETE"], allow_guest=True)
@log()
def v2(type: str, data: dict | None = None, **kwargs):
	"""
	Handle API requests with different HTTP methods.
	The data param (for POST) is converted to a Pydantic model for validation.
	"""

	endpoint = endpoints.get(type)
	if not endpoint:
		return gen_response(404, "Endpoint not found.")
	if frappe.request.method not in endpoint["methods"]:
		return gen_response(405, "Method not allowed.")
	if not _has_permission(type):
		return gen_response(403, "Guest access not allowed for this endpoint.")


	# -------------------- Rate Limiting --------------------#
	rate_limit_config = endpoint.get("rate_limit")
	if rate_limit_config and rate_limit_config.get("enabled"):
		user_id = (
			frappe.local.request_ip if frappe.session.user == "Guest" else frappe.session.user
		)
		limiter = CustomRateLimiter(
			rate_limit_config["limit"], rate_limit_config["window"], user_id
		)
		if not limiter.is_allowed():
			retry_after = limiter.retry_after()
			return gen_response(
				429,
				f"You've reached the maximum number of requests allowed. Please wait {int(retry_after)} seconds before trying again.",
			)

	# -------------------- Data Handling --------------------#
	if frappe.request.headers.get("Content-Type") != "application/json":
		data = {k: v for k, v in frappe.form_dict.items() if k not in {"type", "cmd", "_lang"}}
	else:
		data = data or {}

    # -------------------- Model Validation --------------------#
	model = endpoint.get("model")
	if model:
		data, error = _validate_data(model, data)
		if error:
			return gen_response(400, error)
		
    # -------------------- Function Execution --------------------#
	try:
		if frappe.request.method == "POST":
			frappe.db.begin()
			
		result = endpoint["function"](data) if model else endpoint["function"](**data)

		if frappe.request.method == "POST":
			frappe.db.commit()
	except frappe.AuthenticationError:
		return gen_response(500, frappe.response["message"])
	except Exception as e:
		frappe.log_error(title="ESS Error", message=frappe.get_traceback())
		return gen_response(500, str(e))
	finally:
		if frappe.request.method == "POST":
			frappe.db.close()
	return gen_response(200, frappe.response.get("message"), result)
	

def _has_permission(type: str) -> bool:
	"""Check if guest access is allowed."""
	return get_allow_guest(type) or frappe.session.user != "Guest"


def _validate_data(model, data: dict):
	"""Validate data with Pydantic model and return formatted error if any."""
	try:
		return model(**data), None
	except ValidationError as ve:
		error_details = [f"{error['loc'][0]}: {error['msg']}" for error in ve.errors()]
		return None, "Validation error: " + ", ".join(error_details)


def gen_response(status, message, data=None):
	frappe.response["http_status_code"] = status
	frappe.response["status_code"] = status

	# Determine success or failure based on status code
	if 400 <= status < 600:
		frappe.response["status"] = "fail"
		frappe.response["message"] = BeautifulSoup(str(message)).get_text()  # Clean message for failure cases
	else:
		frappe.response["status"] = "success"
		frappe.response["message"] = message

	# Include data if provided
	if data is not None:
		frappe.response["data"] = data