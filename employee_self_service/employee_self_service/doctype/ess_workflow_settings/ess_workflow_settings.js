// Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("ESS Workflow Settings", {
	refresh(frm) {
		// Restrict the Document link to only show doctypes with an active Workflow
		frm.fields_dict["ess_workflow_documents"].grid.get_field("document").get_query =
			function () {
				return {
					query: "employee_self_service.employee_self_service.doctype.ess_workflow_settings.ess_workflow_settings.get_workflow_doctypes",
				};
			};

		// ── "Fetch Workflow Documents" button ────────────────────────────────
		frm.add_custom_button(__("Fetch Workflow Documents"), function () {
			frappe.call({
				method: "employee_self_service.employee_self_service.doctype.ess_workflow_settings.ess_workflow_settings.fetch_all_workflow_documents",
				freeze: true,
				freeze_message: __("Fetching active workflow documents…"),
				callback(r) {
					if (!r.message || !r.message.length) {
						frappe.msgprint({
							title: __("No active workflows"),
							message: __("No active Workflow documents were found in the system."),
							indicator: "orange",
						});
						return;
					}

					const existing = (frm.doc.ess_workflow_documents || []).map(
						(row) => row.document
					);
					let added = 0;

					r.message.forEach((item) => {
						if (existing.includes(item.document_type)) return;

						const row = frappe.model.add_child(
							frm.doc,
							"ESS Workflow Documents",
							"ess_workflow_documents"
						);
						frappe.model.set_value(row.doctype, row.name, "document", item.document_type);
						frappe.model.set_value(row.doctype, row.name, "list_view_config", item.list_view_config);
						frappe.model.set_value(row.doctype, row.name, "detail_view_config", item.detail_view_config);
						added++;
					});

					frm.refresh_field("ess_workflow_documents");

					if (added > 0) {
						frappe.show_alert({
							message: __("{0} workflow document(s) added with default configuration. Save to persist.", [added]),
							indicator: "green",
						});
						frm.dirty();
					} else {
						frappe.show_alert({
							message: __("All active workflow documents are already in the table."),
							indicator: "blue",
						});
					}
				},
			});
		});
	},
});

// ── Child table: Configure button handler ────────────────────────────────────

frappe.ui.form.on("ESS Workflow Documents", {
	configure(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.document) {
			frappe.msgprint({
				title: __("Select a Document"),
				message: __("Please select a Document before configuring."),
				indicator: "orange",
			});
			return;
		}
		open_configure_dialog(frm, cdt, cdn, row);
	},
});

// ── Configure dialog ─────────────────────────────────────────────────────────

function open_configure_dialog(frm, cdt, cdn, row) {
	frappe.call({
		method: "employee_self_service.employee_self_service.doctype.ess_workflow_settings.ess_workflow_settings.get_doctype_fields",
		args: { doctype: row.document },
		callback(r) {
			if (!r.message) return;

			const meta_fields = r.message; // [{fieldname, label, fieldtype, in_list_view, reqd}]
			const meta_map = Object.fromEntries(meta_fields.map((f) => [f.fieldname, f]));
			const field_options = meta_fields.map((f) => f.fieldname).join("\n");

			// Parse existing configs
			let existing_list = {};
			let existing_detail = {};
			try { existing_list = JSON.parse(row.list_view_config || "{}"); } catch (e) {}
			try { existing_detail = JSON.parse(row.detail_view_config || "{}"); } catch (e) {}

			const list_data = existing_list.fields || [];
			const detail_data = (existing_detail.sections || []).flatMap((s) =>
				s.fields.map((f) => ({
					section_label: s.label,
					fieldname: f.fieldname,
					label: f.label,
					is_badge: f.is_badge || 0,
				}))
			);

			const MAX_LIST = 5;

			const dialog = new frappe.ui.Dialog({
				title: __("Configure: {0}", [row.document]),
				size: "large",
				fields: [
					// ── List View ─────────────────────────────────────────────
					{
						fieldtype: "Section Break",
						label: __("List View Fields"),
						description: __(
							"Choose up to {0} fields for the workflow list card. <code>workflow_state</code> is always appended automatically.",
							[MAX_LIST]
						),
					},
					{
						fieldtype: "Button",
						fieldname: "btn_fill_list",
						label: __("Fill from List View Fields"),
					},
					{
						fieldname: "list_fields",
						fieldtype: "Table",
						cannot_add_rows: false,
						in_place_edit: true,
						fields: [
							{
								fieldname: "fieldname",
								fieldtype: "Autocomplete",
								label: __("Field"),
								options: field_options,
								in_list_view: 1,
								reqd: 1,
								columns: 3,
							},
							{
								fieldname: "label",
								fieldtype: "Data",
								label: __("Display Label"),
								in_list_view: 1,
								columns: 3,
							},
							{
								fieldname: "is_badge",
								fieldtype: "Check",
								label: __("Badge"),
								in_list_view: 1,
								columns: 1,
							},
						],
						data: list_data,
						get_data: () => list_data,
					},

					// ── Detail View ───────────────────────────────────────────
					{
						fieldtype: "Section Break",
						label: __("Detail View Fields"),
						description: __(
							"Group fields into sections. Leave Section blank to use <em>General</em>."
						),
					},
					{
						fieldtype: "Button",
						fieldname: "btn_fill_detail",
						label: __("Fill from Mandatory Fields"),
					},
					{
						fieldname: "detail_fields",
						fieldtype: "Table",
						cannot_add_rows: false,
						in_place_edit: true,
						fields: [
							{
								fieldname: "section_label",
								fieldtype: "Data",
								label: __("Section"),
								in_list_view: 1,
								columns: 2,
							},
							{
								fieldname: "fieldname",
								fieldtype: "Autocomplete",
								label: __("Field"),
								options: field_options,
								in_list_view: 1,
								reqd: 1,
								columns: 3,
							},
							{
								fieldname: "label",
								fieldtype: "Data",
								label: __("Display Label"),
								in_list_view: 1,
								columns: 3,
							},
							{
								fieldname: "is_badge",
								fieldtype: "Check",
								label: __("Badge"),
								in_list_view: 1,
								columns: 1,
							},
						],
						data: detail_data,
						get_data: () => detail_data,
					},
				],
				primary_action_label: __("Save Configuration"),
				primary_action(values) {
					save_config(values);
				},
			});

			// ── Wire up auto-fill buttons after dialog is created ─────────────

			dialog.fields_dict.btn_fill_list.$input.on("click", function () {
				const list_view_fields = meta_fields.filter((f) => f.in_list_view);

				// Ensure workflow_state is present
				const has_state = list_view_fields.some((f) => f.fieldname === "workflow_state");
				if (!has_state) {
					list_view_fields.push({
						fieldname: "workflow_state",
						label: "Status",
						fieldtype: "Data",
						in_list_view: 1,
						reqd: 0,
					});
				}

				const capped = list_view_fields.slice(0, MAX_LIST);
				const new_data = capped.map((f) => ({
					fieldname: f.fieldname,
					label: f.label,
					is_badge: f.fieldname === "workflow_state" ? 1 : 0,
				}));

				fill_grid(dialog.fields_dict.list_fields.grid, new_data);

				frappe.show_alert({
					message: __("{0} field(s) filled from list view definition", [new_data.length]),
					indicator: "green",
				});
			});

			dialog.fields_dict.btn_fill_detail.$input.on("click", function () {
				const reqd_fields = meta_fields.filter((f) => f.reqd);

				// Prepend name + workflow_state if not already present
				const existing_names = new Set(reqd_fields.map((f) => f.fieldname));
				const prefix = [];
				if (!existing_names.has("name")) {
					prefix.push({ fieldname: "name", label: "Document No", fieldtype: "Data" });
				}
				if (!existing_names.has("workflow_state")) {
					prefix.push({ fieldname: "workflow_state", label: "Status", fieldtype: "Data" });
				}

				const all_fields = [...prefix, ...reqd_fields];
				const new_data = all_fields.map((f) => ({
					section_label: "Overview",
					fieldname: f.fieldname,
					label: f.label,
					is_badge: f.fieldname === "workflow_state" ? 1 : 0,
				}));

				fill_grid(dialog.fields_dict.detail_fields.grid, new_data);

				frappe.show_alert({
					message: __("{0} mandatory field(s) filled for detail view", [new_data.length]),
					indicator: "green",
				});
			});

			dialog.show();

			// ── Save helper ───────────────────────────────────────────────────

			function save_config(values) {
				const raw_list = values.list_fields || [];

				if (raw_list.length > MAX_LIST) {
					frappe.msgprint({
						title: __("Too many fields"),
						message: __("List view supports a maximum of {0} fields. You have {1}.", [
							MAX_LIST,
							raw_list.length,
						]),
						indicator: "red",
					});
					return;
				}

				// Always ensure workflow_state is present
				if (!raw_list.some((f) => f.fieldname === "workflow_state")) {
					raw_list.push({ fieldname: "workflow_state", label: "Status", is_badge: 1 });
				}

				function enrich(fields) {
					return fields
						.filter((f) => f.fieldname)
						.map((f) => ({
							fieldname: f.fieldname,
							label: f.label || (meta_map[f.fieldname] && meta_map[f.fieldname].label) || f.fieldname,
							fieldtype: (meta_map[f.fieldname] && meta_map[f.fieldname].fieldtype) || "Data",
							is_badge: f.is_badge ? 1 : 0,
						}));
				}

				const list_config = { fields: enrich(raw_list) };

				// Build detail sections from flat rows
				const raw_detail = values.detail_fields || [];
				const sections_map = {};
				raw_detail
					.filter((f) => f.fieldname)
					.forEach((f) => {
						const sec = (f.section_label || "General").trim();
						if (!sections_map[sec]) sections_map[sec] = { label: sec, fields: [] };
						sections_map[sec].fields.push({
							fieldname: f.fieldname,
							label: f.label || (meta_map[f.fieldname] && meta_map[f.fieldname].label) || f.fieldname,
							fieldtype: (meta_map[f.fieldname] && meta_map[f.fieldname].fieldtype) || "Data",
							is_badge: f.is_badge ? 1 : 0,
						});
					});
				const detail_config = { sections: Object.values(sections_map) };

				frappe.model.set_value(cdt, cdn, "list_view_config", JSON.stringify(list_config));
				frappe.model.set_value(cdt, cdn, "detail_view_config", JSON.stringify(detail_config));

				dialog.hide();
				frappe.show_alert({
					message: __("{0} configured successfully", [row.document]),
					indicator: "green",
				});
				frm.dirty();
			}
		},
	});
}

// ── Utility: replace a dialog grid's data and refresh ────────────────────────

function fill_grid(grid, new_data) {
	// Clear existing rows
	grid.df.data = [];
	grid.grid_rows = [];

	// Add fresh rows
	new_data.forEach((row_data) => {
		const new_row = grid.add_new_row(null, null, true);
		Object.entries(row_data).forEach(([key, val]) => {
			if (key in new_row.doc) new_row.doc[key] = val;
		});
	});

	grid.refresh();
}
