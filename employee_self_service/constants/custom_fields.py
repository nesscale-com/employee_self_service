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
            "fieldname": "attendance_image",
            "label": "Attendance Image",
            "fieldtype": "Attach",
            "insert_after": "location",
        },
        {
            "fieldname": "log_location",
            "label": "Log Location",
            "fieldtype": "Small Text",
            "read_only": 1,
            "insert_after": "attendance_image",
        },
        {
            "fieldname": "out_of_location_checkout",
            "label": "Out of Location Checkout",
            "fieldtype": "Check",
            "insert_after": "log_location",
            "read_only": 1,
        },
        {
            "fieldname": "out_of_location_checkout_reason",
            "label": "Out of Location Checkout Reason",
            "fieldtype": "Small Text",
            "insert_after": "out_of_location_checkout",
            "read_only": 1,
        },
    ],
    "Item Group": [
        {
            "fieldname": "show_in_mobile",
            "label": "Show in Mobile",
            "fieldtype": "Check",
            "insert_after": "column_break_5",
        },
    ],
    "Item": [
        {
            "fieldname": "show_in_mobile",
            "label": "Show in Mobile",
            "fieldtype": "Check",
            "insert_after": "disabled",
        },
    ],
    "Leave Application": [
        {
            "fieldname": "medical_supporting_document",
            "label": "Medical Supporting Document",
            "fieldtype": "Attach",
            "insert_after": "follow_via_email",
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
