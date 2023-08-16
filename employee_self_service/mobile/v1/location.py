import frappe
from frappe import _
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    get_employee_by_user,
    exception_handler,
)

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
            {"employee": current_employee.get("name"), "date": data.get("date")},
            cache=True,
        ):
            location_doc = frappe.get_doc(
                dict(
                    doctype="Employee Location",
                    employee=current_employee.get("name"),
                    date=data.get("date"),
                )
            )
            location_doc.update(data)
            location_doc.insert()
        else:
            location_doc = frappe.get_doc(
                "Employee Location",
                {
                    "employee": current_employee.get("name"),
                    "date": data.get("date"),
                },
            )
            for location in data.get("location"):
                location_doc.append("location", location)

            # Load the formatted JSON string back into a Python object (dictionary)
            # parsed_json = json.loads(

            # )

            # Convert the Python object back to a compact JSON string
            compact_json = """{
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
          [72.854633, 19.081521]
        ]
      }
    }
  ]
}
"""
            # frappe.log_error(title="ESS Mobile App debug", message=compact_json)
            # location_doc.location_map = compact_json
            location_doc.save()

        gen_response(200, "Location updated successfully.")

    except Exception as e:
        return exception_handler(e)
