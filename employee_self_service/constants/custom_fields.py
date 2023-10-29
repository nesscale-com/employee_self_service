import frappe

CUSTOM_FIELDS = {
    "Branch": [
        {
            "fieldname": "latitude",
            "label": "latitude",
            "fieldtype": "Data",
            "insert_after": "branch",
            "translatable": 1,
        },
        {
            "fieldname": "longitude",
            "label": "longitude",
            "fieldtype": "Data",
            "insert_after": "latitude",
            "translatable": 1,
        },
        {
            "fieldname": "radius",
            "label": "radius",
            "fieldtype": "Data",
            "insert_after": "longitude",
            "translatable": 1,
        },
    ],
    "Employee Checkin": [
        {
            "fieldname": "location",
            "label": "Location",
            "fieldtype": "Small Text",
            "insert_after": "shift_actual_end",
            "translatable": 1,
            "read_only": 1,
        },
        {
            "fieldname": "odometer_reading",
            "label": "Odometer reading",
            "fieldtype": "Data",
            "insert_after": "log_type",
            "translatable": 1,
            "read_only": 1,
        },
        {
            "fieldname": "attendance_image",
            "label": "Attendance Image",
            "fieldtype": "Attach",
            "insert_after": "location",
        },
    ],
}


def delete_custom_fields(custom_fields):
    for doctypes, fields in custom_fields.items():
        if isinstance(fields, dict):
            # only one field
            fields = [fields]

        if isinstance(doctypes, str):
            # only one doctype
            doctypes = (doctypes,)

        for doctype in doctypes:
            frappe.db.delete(
                "Custom Field",
                {
                    "fieldname": ("in", [field["fieldname"] for field in fields]),
                    "dt": doctype,
                },
            )

            frappe.clear_cache(doctype=doctype)
