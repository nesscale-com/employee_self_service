// Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Target Entry", {
    refresh: function(frm){
        frm.trigger("set_team_employee");
        frm.trigger("set_team_item_group");

        frm.set_df_property("item_group_wise_target", "cannot_add_rows", true);
        frm.set_df_property("item_group_wise_target", "cannot_delete_rows", true);
    },
    employee: function(frm) {
        frm.trigger("set_sales_person");
        frm.trigger("set_team_employee");
        frm.trigger("set_team_item_group");
    },
    selector: function(frm){
        frm.trigger("set_team_employee");
        frm.trigger("set_team_item_group");
    },
    set_sales_person: function(frm){
        frm.set_value("sales_person", "");
        frm.set_value("is_group", "");

        frm.call({
            method: "set_sales_person",
            doc: frm.doc,
            callback: function(r) {
                if (r && r.message) {
                    frm.refresh_field("sales_person");
                }
            }
        });
    },
    set_team_employee: function(frm) {
		if (frm.doc.employee && frm.doc.is_group == 1) {
			const query_config = () => {
                let filters = { employee: frm.doc.employee };
                if (frm.doc.selector !== "Item Group") {
                    let selected_employees = (frm.doc.team_targets || []).map(d => d.employee);
                    filters.exclude_employees = selected_employees;
                }

                return {
                    query: "employee_self_service.employee_self_service.doctype.employee_target_entry.employee_target_entry.get_team_employee",
                    filters: filters
                };
            };

			if (frm.doc.selector === "Item Group") {
				frm.fields_dict['item_group_wise_team_targets'].grid.get_field('employee').get_query = query_config;
			} else {
				frm.fields_dict['team_targets'].grid.get_field('employee').get_query = query_config;
			}
		}
	},
    set_team_item_group: function(frm) {
        if (frm.doc.employee && frm.doc.is_group == 1 && frm.doc.selector === "Item Group") {

            const allowed_item_groups = (frm.doc.item_group_wise_target || []).map(d => d.item_group);
            frm.fields_dict['item_group_wise_team_targets'].grid.get_field('item_group').get_query = function(doc, cdt, cdn) {
                return {
                    filters: {
                        name: ["in", allowed_item_groups]
                    }
                };
            };
        }
    },
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
                        if(frm.doc.is_group == 0){
                            const grid = frm.fields_dict["item_group_wise_target"].grid;
                            grid.update_docfield_property("team_target", "read_only", 1);
                            grid.update_docfield_property("team_achieved", "read_only", 1);
                            grid.update_docfield_property("team_progress", "read_only", 1);
                        }
                        else{
                            if (frm.doc.selector == "Item Group"){
                                frm.clear_table("item_group_wise_team_targets");
                                r.message.forEach(row => {
                                    let child = frm.add_child("item_group_wise_team_targets");
                                    child.item_group = row.item_group;
                                });
                            }
                        }
                        frm.refresh_field("item_group_wise_target");
                        frm.refresh_field("item_group_wise_team_targets");
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
