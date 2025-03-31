// Copyright (c) 2022, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Self Service Settings', {
	setup: function (frm) {
		frm.set_query("default_payable_account", function () {
			return {
				filters: {
					"account_type": "Payable",
					"is_group": 0
				}
			};
		})
		frm.set_query("default_print_format", function () {
			return {
				filters: {
					"doc_type": "Salary Slip"
				}
			};
		})
	}
});
