# Copyright (c) 2022, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from employee_self_service.setup import disable_geolocation_tracking


class EmployeeSelfServiceSettings(Document):
    def on_update(self):
        disable_geolocation_tracking()
