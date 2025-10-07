// Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Target Entry", {
	target_template: function(frm) {
        if (frm.doc.target_template) {
            frm.call({
                method: "get_template_item_groups",
                doc: frm.doc,
                callback: function (r) {
                    if (r.message && r.message.length > 0) {
                        frm.clear_table("item_group_wise_target");
                        r.message.forEach(row => {
                            let child = frm.add_child("item_group_wise_target");
                            child.item_group = row.item_group;
                        });
                        frm.refresh_field("item_group_wise_target");
                    }
                }
            });
        } else {
            frm.clear_table("item_group_wise_target");
            frm.refresh_field("item_group_wise_target");
        }
    },
    month: function(frm) {
        frm.trigger("set_date_range");
    },
    quarter: function(frm) {
        frm.trigger("set_date_range");
    },
    fiscal_year: function(frm) {
        frm.trigger("set_date_range");
    },
    set_date_range: function(frm) {
        if (!frm.doc.fiscal_year || !frm.doc.frequency) return;
        frm.call({
            method: "get_date_range",
            doc: frm.doc,
            callback: function(r) {
                if (r.message) {
                    frm.set_value("start_date", r.message.start_date);
                    frm.set_value("end_date", r.message.end_date);
                }
            }
        });
    }
});
