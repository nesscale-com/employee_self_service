// Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Target Template", {
    refresh(frm) {
        //
    }
});

frappe.ui.form.on("Target Item Group List", {
    item_group: function(frm, cdt, cdn) {
        set_item_group_query(frm);
    }
});

function set_item_group_query(frm) {
    frm.fields_dict['item_group_list'].grid.get_field('item_group').get_query = function(doc, cdt, cdn) {
        let child_row = locals[cdt][cdn];
        let selected_groups = [];
        
        if (doc.item_group_list) {
            doc.item_group_list.forEach(function(row) {
                if (row.item_group && row.name !== child_row.name) {
                    selected_groups.push(row.item_group);
                }
            });
        }
        
        return {
            query: 'employee_self_service.employee_self_service.doctype.employee_target_template.employee_target_template.get_filtered_item_groups',
            filters: {
                'selected_groups': selected_groups
            }
        };
    };
    
    frm.refresh_field('item_group_list');
}
