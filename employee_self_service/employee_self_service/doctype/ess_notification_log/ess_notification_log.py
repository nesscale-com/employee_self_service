# Copyright (c) 2024, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import json

class ESSNotificationLog(Document):
	def after_insert(self):
		target_site_url = "https://notification.nesscale.com/api/method/ncs_nesscale.api.send_push_notification"
		
		erp_url = frappe.utils.get_url()
		
		# Prepare the payload
		payload = {
			"product_name": "Nesscale ESS",
			"subject": self.subject,
			"message": self.message,
			"notification_type": "info",
			"tokens": [self.token],
			"erp_url": erp_url
		}
		# Set your headers for authentication (API key and secret)
		headers = {
			"Content-Type": "application/json"
		}
		
		try:
			# Send the POST request
			response = requests.post(target_site_url, headers=headers, data=json.dumps(payload))
			# Check the response
			if response.status_code == 200:
				print("Notification sent successfully!")
			else:
				frappe.log_error(title="ESS Push Notification Error",message=f"Failed to send notification. Status Code: {response.status_code}, Response: {response.text}")
		except Exception as e:
			frappe.log_error(title="ESS Push Notification Error",message=frappe.get_traceback())

