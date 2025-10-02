// Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Target Template", {
	selector: function(frm) {
        if (frm.doc.selector === "Item Group") {
            frm.clear_table("customer_group_list");
            frm.refresh_field("customer_group_list");
        }
        else if (frm.doc.selector === "Customer Group") {
            frm.clear_table("item_group_list");
            frm.refresh_field("item_group_list");
        }
    }
});

frappe.ui.form.on("Target Item Group List", {
    item_group: function(frm, cdt, cdn) {
        set_group_query(frm, "item_group_list", "item_group", "Item Group");
    }
});

frappe.ui.form.on("Target Customer Group List", {
    customer_group: function(frm, cdt, cdn) {
        set_group_query(frm, "customer_group_list", "customer_group", "Customer Group");
    }
});

function set_group_query(frm, child_table_field, fieldname, doctype) {
    frm.fields_dict[child_table_field].grid.get_field(fieldname).get_query = function (doc, cdt, cdn) {
        let child_row = locals[cdt][cdn];
        let selected_groups = [];

        if (doc[child_table_field]) {
            doc[child_table_field].forEach(function (row) {
                if (row[fieldname] && row.name !== child_row.name) {
                    selected_groups.push(row[fieldname]);
                }
            });
        }

        return {
            query: "employee_self_service.employee_self_service.doctype.employee_target_template.employee_target_template.get_filtered_groups",
            filters: {
                "selected_groups": selected_groups,
                "doctype_name": doctype
            }
        };
    };

    frm.refresh_field(child_table_field);
}


