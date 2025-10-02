# Copyright (c) 2025, Nesscale Solutions Private Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeTargetTemplate(Document):
    pass


@frappe.whitelist()
def get_filtered_groups(doctype, txt, searchfield, start, page_len, filters):
    selected_groups = filters.get("selected_groups", []) or []
    doctype_name = filters.get("doctype_name")

    all_groups = frappe.get_all(
        doctype_name, fields=["name", "parent_" + frappe.scrub(doctype_name)]
    )
    parent_field = "parent_" + frappe.scrub(doctype_name)

    exclude_set = set()

    for group in selected_groups:
        if not group:
            continue

        exclude_set.add(group)
        for item in all_groups:
            # add parent
            if item.name == group and item.get(parent_field):
                exclude_set.add(item.get(parent_field))

            # add children
            if item.get(parent_field) == group:
                exclude_set.add(item.name)

    results = []
    for item in all_groups:
        if item.name in exclude_set:
            continue
        results.append([item.name, item.get(parent_field)])

    return results
