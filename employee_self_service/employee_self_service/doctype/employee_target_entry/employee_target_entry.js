// Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Target Entry", {
    onload: function(frm){
        frm.set_df_property("item_group_wise_target", "cannot_add_rows", true);
		frm.set_df_property("item_group_wise_target", "cannot_delete_rows", true);
        frm.set_df_property("customer_group_wise_target", "cannot_add_rows", true);
		frm.set_df_property("customer_group_wise_target", "cannot_delete_rows", true);
    },
	target_template: function(frm) {
        if (frm.doc.target_template) {
            frm.call({
                method: "get_template_groups",
                doc: frm.doc,
                callback: function (r) {
                    if (r.message && r.message.child_table && r.message.rows) {
                        frm.clear_table(r.message.child_table);
                        r.message.rows.forEach(row => {
                            let child = frm.add_child(r.message.child_table);
                            if (row.item_group) {
                                child.item_group = row.item_group;
                            }
                            if (row.customer_group) {
                                child.customer_group = row.customer_group;
                            }
                        });
                        frm.refresh_field(r.message.child_table);
                    }
                }
            });
        } else {
            frm.clear_table("item_group_wise_target");
            frm.clear_table("customer_group_wise_target");
            frm.refresh_field("item_group_wise_target");
            frm.refresh_field("customer_group_wise_target");
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
