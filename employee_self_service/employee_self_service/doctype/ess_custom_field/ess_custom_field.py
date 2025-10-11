# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ESSCustomField(Document):
    def validate(self):
        frappe.throw(
            msg="""
			<div style="text-align: center; padding: 20px;">
				<h3>🚧 Feature Under Development</h3>
				<p style="margin: 15px 0;">This custom field feature is currently under active development and will be available soon.</p>
				<p style="margin: 15px 0;">We're working hard to bring you the best experience with advanced customization options.</p>
				<div style="margin-top: 20px;">
					<a href="https://ess.nesscale.app" target="_blank" style="
						background-color: #007bff;
						color: white;
						padding: 10px 20px;
						text-decoration: none;
						border-radius: 5px;
						font-weight: bold;
					">Contact Us for Updates</a>
				</div>
				<p style="margin-top: 15px; font-size: 12px; color: #666;">
					Stay tuned for exciting new features!
				</p>
			</div>
			""",
            title="Feature Coming Soon",
        )
