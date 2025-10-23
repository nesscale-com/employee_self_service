// Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("ESS Custom Field", {
	refresh(frm) {
		// Make all fields readonly since feature is under development
		frm.disable_form();

		// Show development notice banner
		frm.dashboard.add_comment(`
			<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin: 10px 0;">
				<div style="display: flex; align-items: center;">
					<span style="font-size: 20px; margin-right: 10px;">🚧</span>
					<div>
						<strong>Development Mode Active</strong><br>
						<small>This feature is under development. All fields are read-only.
						<a href="https://ess.nesscale.app" target="_blank" style="color: #007bff;">Contact us</a> for updates.</small>
					</div>
				</div>
			</div>
		`, "yellow");

		// Also make specific child table readonly if it exists
		frm.fields_dict.custom_fields && frm.fields_dict.custom_fields.grid &&
		frm.fields_dict.custom_fields.grid.toggle_enable(false);
	},

	onload(frm) {
		// Additional readonly enforcement on load
		if (frm.doc.__islocal) {
			// For new documents, show a more prominent message
			frappe.msgprint({
				title: __('Feature Under Development'),
				indicator: 'orange',
				message: `
					<div style="text-align: center; padding: 10px;">
						<h4>🚧 This feature is currently being developed</h4>
						<p>We're working on bringing you advanced custom field capabilities.</p>
						<p><a href="https://ess.nesscale.app" target="_blank" style="color: #007bff;">Contact us</a> to get notified when it's ready!</p>
					</div>
				`
			});
		}
	}
});
