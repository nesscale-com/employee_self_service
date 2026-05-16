// Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Details Update Request", {
    refresh(frm) {
        render_diff(frm);
    },
});

const FIELD_LABELS = {
    first_name: __("Full Name"),
    gender: __("Gender"),
    date_of_birth: __("Date of Birth"),
    date_of_joining: __("Date of Joining"),
    cell_number: __("Mobile"),
    personal_email: __("Personal Email"),
    current_address: __("Current Address"),
    emergency_phone_number: __("Emergency Phone Number"),
    marital_status: __("Marital Status"),
    blood_group: __("Blood Group"),
};

function render_diff(frm) {
    const wrapper = frm.fields_dict.table_html.$wrapper;

    if (!frm.doc.data) {
        wrapper.empty();
        return;
    }

    let data;

    try {
        data = JSON.parse(frm.doc.data);
    } catch {
        wrapper.empty();
        return;
    }

    const old_values = data.old || {};
    const new_values = data.new || {};

    let rows = "";

    Object.entries(new_values).forEach(([field, value]) => {

        if (field === "education") return;

        rows += `
            <tr>
                <td>${FIELD_LABELS[field] || field}</td>

                <td style="background:#fff0f0;">
                    ${frappe.utils.escape_html(String(old_values[field] || "—"))}
                </td>

                <td style="background:#f0fff4;">
                    ${frappe.utils.escape_html(String(value || "—"))}
                </td>
            </tr>
        `;
    });

    if (new_values.education?.length) {

        const render_education_table = (list = []) => {

            if (!list.length) {
                return `<div class="text-muted">—</div>`;
            }

            return `
                <table class="table table-sm table-bordered mb-0">
                    <thead>
                        <tr>
                            <th>${__("School/University")}</th>
                            <th>${__("Qualification")}</th>
                            <th>${__("Level")}</th>
                            <th>${__("Year")}</th>
                        </tr>
                    </thead>

                    <tbody>
                        ${list.map(row => `
                            <tr>
                                <td>${frappe.utils.escape_html(row.school_univ || "")}</td>
                                <td>${frappe.utils.escape_html(row.qualification || "")}</td>
                                <td>${frappe.utils.escape_html(row.level || "")}</td>
                                <td>${frappe.utils.escape_html(row.year_of_passing || "")}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
        };

        rows += `
            <tr>
                <td>${__("Education")}</td>

                <td style="background:#fff0f0;">
                    ${render_education_table(old_values.education)}
                </td>

                <td style="background:#f0fff4;">
                    ${render_education_table(new_values.education)}
                </td>
            </tr>
        `;
    }

    if (!rows) {
        wrapper.html(`
            <div class="text-muted">
                ${__("No changes requested.")}
            </div>
        `);
        return;
    }

    wrapper.html(`
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th style="width:20%">
                        ${__("Field")}
                    </th>

                    <th style="width:40%">
                        ${__("Old Value")}
                    </th>

                    <th style="width:40%">
                        ${__("New Value")}
                    </th>
                </tr>
            </thead>

            <tbody>
                ${rows}
            </tbody>
        </table>
    `);
}