# Copyright (c) 2023, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe

import json
from frappe.model.document import Document


class EmployeeLocation(Document):
    def validate(self):
        self.set_map_location()

    def set_map_location(self):
        location_list = []
        for location in self.location:
            location_list.append([location.longitude, location.latitude])
        map_json = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": location_list,
                    },
                },
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        "coordinates": location_list[0],
                    },
                },
            ],
        }

        self.location_map = json.dumps(map_json)
