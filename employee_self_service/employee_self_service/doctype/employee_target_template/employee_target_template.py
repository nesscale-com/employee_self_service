# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeTargetTemplate(Document):
    pass


@frappe.whitelist()
def get_filtered_item_groups(doctype, txt, searchfield, start, page_len, filters):
    selected_groups = filters.get("selected_groups", [])

    if not selected_groups:
        selected_groups = []

    all_item_groups = frappe.get_all("Item Group", fields=["name", "parent_item_group"])
    exclude_set = set()

    for group in selected_groups:
        if not group:
            continue

        exclude_set.add(group)
        for item in all_item_groups:
            # add parent
            if item.name == group and item.parent_item_group:
                exclude_set.add(item.parent_item_group)

            # add children
            if item.parent_item_group == group:
                exclude_set.add(item.name)

    results = []
    for item in all_item_groups:
        if item.name in exclude_set:
            continue
        results.append([item.name, item.parent_item_group])
    return results
