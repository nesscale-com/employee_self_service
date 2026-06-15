# Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document


class ESSVisit(Document):
	def before_insert(self):
		self.set_employee_from_session()

	def validate(self):
		self.set_employee_from_session()

	def on_update(self):
		self.auto_tag_customer_location()

	def set_employee_from_session(self):
		"""Derive employee/user from the logged-in session when not supplied.

		The mobile common CRUD API does not pass employee/user, so we resolve
		them server-side from the session user. This is the secure source of
		truth — we never rely on the client to assert who owns the visit. Any
		client-sent value is only kept as a fallback (e.g. desk users creating
		on behalf of others); when absent we always fill from the session.
		"""
		if not self.employee:
			self.employee = frappe.db.get_value(
				"Employee", {"user_id": frappe.session.user}, "name"
			)

		if self.employee and not self.user:
			self.user = frappe.db.get_value("Employee", self.employee, "user_id")

	def auto_tag_customer_location(self):
		"""Geo-tag the customer from the visit's start location.

		When ESS Field Staff Settings is set to auto geo-tag customers based on
		Visit, and an existing customer has no Customer Location yet, store the
		coordinates captured at visit start. Later visits can then geofence
		against this point. Only the first visit creates it; we never overwrite
		an existing location here.
		"""
		if self.customer_type != "Existing" or not self.customer:
			return

		based_on = frappe.db.get_single_value(
			"ESS Field Staff Settings", "customer_geo_tagging_auto_based_on"
		)
		if based_on != "Visit":
			return

		if frappe.db.exists("Customer Location", {"customer": self.customer}):
			return

		coords = self.get_lat_long(self.visit_start_location)
		if not coords:
			return

		latitude, longitude = coords
		frappe.get_doc(
			{
				"doctype": "Customer Location",
				"customer": self.customer,
				"latitude": str(latitude),
				"longitude": str(longitude),
			}
		).insert(ignore_permissions=True)

	@staticmethod
	def get_lat_long(geolocation):
		"""Pull (latitude, longitude) out of a Frappe Geolocation GeoJSON value.

		GeoJSON coordinates are stored as [longitude, latitude]; we return them
		in (latitude, longitude) order. Returns None when no point is present.
		"""
		if not geolocation:
			return None
		try:
			data = json.loads(geolocation) if isinstance(geolocation, str) else geolocation
			for feature in data.get("features") or []:
				geometry = feature.get("geometry") or {}
				if geometry.get("type") == "Point" and geometry.get("coordinates"):
					longitude, latitude = geometry["coordinates"][:2]
					return latitude, longitude
		except Exception:
			return None
		return None
