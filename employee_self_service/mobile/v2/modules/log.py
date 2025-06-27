import functools
import frappe
from frappe.exceptions import AuthenticationError, ValidationError
from frappe import _

class log:
    def __init__(self):
        pass

    def __call__(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            user = frappe.session.user
            ip = frappe.local.request_ip
            function_name = fn.__name__
            module = fn.__module__
            api_name = kwargs.get("type", "")

            # Optional headers
            latitude = frappe.local.request.headers.get("X-Latitude", "")
            longitude = frappe.local.request.headers.get("X-Longitude", "")

            try:
                # Execute the main function
                result = fn(*args, **kwargs)

                # Log the successful request
                self._log_api_call(
                    user, ip, function_name, module, api_name,
                    latitude, longitude, args, kwargs, result, "", 200
                )
                return result

            except (AuthenticationError, ValidationError) as e:
                frappe.response["http_status_code"] = e.http_status_code
                frappe.response["message"] = str(e)

                self._log_api_call(
                    user, ip, function_name, module, api_name,
                    latitude, longitude, args, kwargs, "", str(e), e.http_status_code
                )
                return str(e)

            except Exception as e:
                frappe.log_error(title="ESS API Error", message=frappe.get_traceback())
                frappe.response["http_status_code"] = 500

                self._log_api_call(
                    user, ip, function_name, module, api_name,
                    latitude, longitude, args, kwargs, "", str(e), 500
                )
                return str(e)

        return decorated

    @staticmethod
    def _log_api_call(user, ip, function_name, module, api_name,
                      latitude, longitude, args, kwargs, result, exception, http_status_code):
        """Log the API request and response to ESS API Log."""
        frappe.get_doc({
            "doctype": "ESS API Log",
            "timestamp": frappe.utils.now(),
            "user": user,
            "ip": ip,
            "latitude": latitude,
            "longitude": longitude,
            "function_name": function_name,
            "module": module,
            "api_name": api_name,
            "arguments": str(args),
            "kwarguments": str(kwargs),
            "result": str(result),
            "exception": str(exception),
            "http_status_code": http_status_code,
        }).insert(ignore_permissions=True)
