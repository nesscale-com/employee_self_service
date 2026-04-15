# Copyright (c) 2022, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeSelfServiceSettings(Document):

    def validate(self):
        if self.location_validate == 0:
            self.update_hr_settings_geolocation()

    def update_hr_settings_geolocation(self):
        if frappe.db.exists("DocType", "HR Settings"):
            frappe.db.set_value(
                "HR Settings",
                "HR Settings",
                "allow_geolocation_tracking",
                0,
            )
