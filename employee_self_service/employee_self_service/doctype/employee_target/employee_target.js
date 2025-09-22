// Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Target", {
	select_all_employee: function (frm) {
        if (frm.doc.select_all_employee) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Employee",
                    filters: { status: "Active" },
                    fields: ["name", "employee_name"],
                    limit_page_length: 20,
                },
                callback: function (r) {
                    if (!r.message) return;

                    frm.clear_table("employee_list");

                    r.message.forEach((emp) => {
                        let row = frm.add_child("employee_list");
                        row.employee = emp.name;
                    });

                    frm.refresh_field("employee_list");
                    frappe.show_alert({
                        message: __("All active employees added."),
                        indicator: "green",
                    });
                },
            });
        } else {
            frm.clear_table("employee_list");
            frm.refresh_field("employee_list");
        }
    },
});
