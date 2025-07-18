// Copyright (c) 2023, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('ESS Post', {
	validate: function(frm) {
        if (!frm.doc.category) {
            frappe.throw(__('Category is mandatory'));
        }
    }
});
