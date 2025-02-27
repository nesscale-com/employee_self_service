import frappe
from employee_self_service.mobile.v1.api_utils import (
    gen_response,
    ess_validate,
    exception_handler,
    get_employee_by_user,
    check_workflow_exists,
    get_global_defaults,
    get_attachments,
)
from frappe.utils import today

@frappe.whitelist()
@ess_validate(methods=["GET"])
def get_location():
    try:
        geofencing_based_on = frappe.db.get_value("Employee Self Service Settings","Employee Self Service Settings","geofencing_based_on")
        emp_data = get_employee_by_user(frappe.session.user,fields=["name","branch"])
        locations = []
        if geofencing_based_on == "Branch":
            if emp_data.get("branch"):
                branch_doc = frappe.get_doc("Branch",emp_data.get("branch"))
                locations.append({"latitude":branch_doc.get("latitude"),"longitude":branch_doc.get("longitude"),"radius":branch_doc.get("radius")})
        if geofencing_based_on == "ESS Location":
            filters = [
                ["from_date","<=",today()],
                ["to_date",">=",today()],
                ["employee","=",emp_data.get("name")]
            ]
            location_assignment = frappe.get_all("ESS Location Assignment",filters=filters,fields=["name","location"])
            for row in location_assignment:
                location_doc = frappe.get_doc("ESS Location",row.location)
                locations.append({"latitude":location_doc.get("latitude"),"longitude":location_doc.get("longitude"),"radius":location_doc.get("radius")})
        return gen_response(200,"ESS Location get successfully",locations)
    except Exception as e:
        return exception_handler(e)
