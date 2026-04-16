import frappe
from frappe.utils import today

from employee_self_service.mobile.v2.api_utils import (
    check_workflow_exists,
    ess_validate,
    exception_handler,
    gen_response,
    get_attachments,
    get_employee_by_user,
    get_ess_settings,
    get_global_defaults,
)


@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_location():
    try:
        emp_data = get_employee_by_user(frappe.session.user, fields=["name", "branch"])
        ess_settings = get_ess_settings()
        geofencing_based_on = ess_settings.get("geofencing_based_on")
        # if not ess_settings.get("location_validate"):
        # if not emp_data.get("branch") and geofencing_based_on == "Branch":
        # 	return gen_response(500, "Branch not assigned to employee!")

        # if geofencing_based_on == "ESS Location":
        # 	filters = [
        # 		["from_date", "<=", today()],
        # 		["to_date", ">=", today()],
        # 		["employee", "=", emp_data.get("name")],
        # 	]
        # 	location_assignments = frappe.get_all(
        # 		"ESS Location Assignment", filters=filters, fields=["name"]
        # 	)
        # if len(location_assignments) < 1:
        # 	return gen_response(500, "ESS Location not assigned to employee!")

        locations = []
        if geofencing_based_on == "Branch":
            if emp_data.get("branch"):
                branch_doc = frappe.get_doc("Branch", emp_data.get("branch"))
                locations.append(
                    {
                        "latitude": branch_doc.get("latitude"),
                        "longitude": branch_doc.get("longitude"),
                        "radius": branch_doc.get("radius"),
                    }
                )
        if geofencing_based_on == "ESS Location":
            filters = [
                ["from_date", "<=", today()],
                ["to_date", ">=", today()],
                ["employee", "=", emp_data.get("name")],
            ]
            location_assignment = frappe.get_all(
                "ESS Location Assignment", filters=filters, fields=["name", "location"]
            )
            for row in location_assignment:
                location_doc = frappe.get_doc("ESS Location", row.location)
                locations.append(
                    {
                        "latitude": location_doc.get("latitude"),
                        "longitude": location_doc.get("longitude"),
                        "radius": location_doc.get("radius"),
                    }
                )
        return gen_response(200, "ESS Location get successfully", locations)
    except Exception as e:
        return exception_handler(e)

"""save user location"""

"""{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [72.855663, 19.080709],
          [72.871113, 19.09531],
          [72.873344, 19.078438],
          [72.86459, 19.067731],
          [72.848454, 19.073084],
          [72.854633, 19.081521],
          [72.840214, 19.105204]
        ]
      }
    }
  ]
}
"""


@frappe.whitelist()
@ess_validate(methods=["POST"])
def user_location(*args, **kwargs):
    try:
        data = kwargs
        if not data.get("location"):
            return gen_response(500, "location is required.")
        current_employee = get_employee_by_user(frappe.session.user)
        if not frappe.db.exists(
            "Employee Location",
            {"employee": current_employee.get("name"), "date": today()},
            cache=True,
        ):
            location_doc = frappe.get_doc(
                doctype="Employee Location", employee=current_employee.get("name")
            )
            location_doc.update(data)
            location_doc.insert(ignore_permissions=True)
        else:
            location_doc = frappe.get_doc(
                "Employee Location",
                {"employee": current_employee.get("name")},
            )
            for location in data.get("location"):
                location_doc.append("location", location)

            # Load the formatted JSON string back into a Python object (dictionary)
            # parsed_json = json.loads(

            # )

            # Convert the Python object back to a compact JSON string
            # frappe.log_error(title="ESS Mobile App debug", message=compact_json)
            # location_doc.location_map = compact_json
            location_doc.save(ignore_permissions=True)

        gen_response(200, "Location updated successfully.")

    except Exception as e:
        return exception_handler(e)
