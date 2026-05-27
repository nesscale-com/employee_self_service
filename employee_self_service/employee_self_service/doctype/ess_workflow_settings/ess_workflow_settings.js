// Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

// ─── CSS (injected once) ──────────────────────────────────────────────────────

const _ESS_CSS = `
/* Layout */
.ess-cfg { font-size: 13px; }
.ess-cfg-row { display: flex; gap: 14px; }
.ess-cfg-col-avail { flex: 0 0 230px; min-width: 0; }
.ess-cfg-col-main  { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }

/* Panel chrome */
.ess-panel {
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  overflow: hidden;
  background: var(--card-bg);
}
.ess-panel-hdr {
  padding: 7px 12px;
  background: var(--bg-light-gray, #f4f5f7);
  font-weight: 600; font-size: 11px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
  display: flex; align-items: center; justify-content: space-between;
}

/* Available-field chips */
.ess-search-wrap { padding: 6px 8px; border-bottom: 1px solid var(--border-color); }
.ess-search { width: 100%; border: none; outline: none; font-size: 12px; background: transparent; }
.ess-avail-chips { overflow-y: auto; max-height: 340px; padding: 8px; display: flex; flex-wrap: wrap; gap: 5px; }
.ess-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 9px; border-radius: 12px; cursor: pointer;
  border: 1px solid var(--border-color); background: var(--card-bg);
  font-size: 11px; user-select: none; transition: border-color .12s, color .12s;
}
.ess-chip:hover:not(.ess-chip-used) { border-color: var(--primary); color: var(--primary); }
.ess-chip-used { opacity: .35; cursor: not-allowed; pointer-events: none; }
.ess-chip-type { font-size: 10px; color: var(--text-muted); }

/* Count badge */
.ess-slot-badge {
  font-size: 10px; padding: 1px 7px; border-radius: 8px;
  background: var(--blue-100, #dbeafe); color: var(--blue-500, #3b82f6); font-weight: 600;
}
.ess-slot-badge.warn { background: var(--orange-100, #ffedd5); color: var(--orange-500, #f97316); }

/* Selected-items list */
.ess-items-wrap { padding: 6px; display: flex; flex-direction: column; gap: 4px; min-height: 80px; }
.ess-drop-hint {
  text-align: center; color: var(--text-muted); font-size: 12px;
  padding: 20px; border: 2px dashed var(--border-color);
  border-radius: var(--border-radius); margin: 4px;
}
.ess-items-wrap.drag-over { background: var(--blue-50, #eff6ff); border-radius: var(--border-radius); }
.ess-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; border-radius: var(--border-radius);
  border: 1px solid var(--border-color); background: var(--card-bg);
}
.ess-item:hover { border-color: var(--primary-light, #93c5fd); box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.ess-item.dragging { opacity: .45; }
.ess-drag-handle { cursor: grab; color: var(--text-muted); font-size: 16px; flex-shrink: 0; line-height: 1; }
.ess-drag-handle:active { cursor: grabbing; }
.ess-item-fname { font-size: 10px; color: var(--text-muted); flex-shrink: 0; width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ess-item-label {
  flex: 1; border: none; outline: none; background: transparent;
  font-size: 12px; font-weight: 500; min-width: 60px;
  border-bottom: 1px solid transparent; transition: border-color .12s;
}
.ess-item-label:focus { border-bottom-color: var(--primary); }
.ess-item-slot { flex-shrink: 0; font-size: 11px; padding: 2px 4px; border: 1px solid var(--border-color); border-radius: var(--border-radius); background: var(--card-bg); cursor: pointer; }
.ess-badge-lbl { display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--text-muted); flex-shrink: 0; cursor: pointer; }
.ess-remove-btn {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); font-size: 18px; line-height: 1;
  padding: 0 2px; flex-shrink: 0; transition: color .12s;
}
.ess-remove-btn:hover { color: var(--red-500, #ef4444); }

/* Fill buttons */
.ess-fill-row { display: flex; gap: 7px; flex-wrap: wrap; margin-bottom: 2px; }
.ess-fill-btn {
  font-size: 11px; padding: 3px 10px; border-radius: var(--border-radius);
  border: 1px solid var(--border-color); background: var(--card-bg); cursor: pointer;
  transition: border-color .12s, color .12s;
}
.ess-fill-btn:hover { border-color: var(--primary); color: var(--primary); }

/* Section builders (detail view) */
.ess-sections-wrap { display: flex; flex-direction: column; gap: 8px; }
.ess-section { border: 1px solid var(--border-color); border-radius: var(--border-radius-md); overflow: hidden; background: var(--card-bg); }
.ess-section-hdr { display: flex; align-items: center; gap: 8px; padding: 7px 12px; background: var(--bg-light-gray, #f4f5f7); border-bottom: 1px solid var(--border-color); }
.ess-section-name { flex: 1; border: none; outline: none; background: transparent; font-size: 12px; font-weight: 600; border-bottom: 1px solid transparent; transition: border-color .12s; }
.ess-section-name:focus { border-bottom-color: var(--primary); }
.ess-remove-section { background: none; border: none; cursor: pointer; color: var(--text-muted); font-size: 16px; padding: 0; transition: color .12s; }
.ess-remove-section:hover { color: var(--red-500, #ef4444); }
.ess-section-items { padding: 6px; display: flex; flex-direction: column; gap: 4px; min-height: 44px; }
.ess-section-items.drag-over { background: var(--blue-50, #eff6ff); border-radius: var(--border-radius); }
.ess-add-section {
  padding: 6px; border: 1px dashed var(--border-color); border-radius: var(--border-radius-md);
  text-align: center; cursor: pointer; font-size: 12px; color: var(--text-muted); transition: all .12s;
}
.ess-add-section:hover { border-color: var(--primary); color: var(--primary); }
`;

let _css_injected = false;
function _inject_css() {
	if (_css_injected) return;
	const el = document.createElement("style");
	el.textContent = _ESS_CSS;
	document.head.appendChild(el);
	_css_injected = true;
}

// ─── Parent form ──────────────────────────────────────────────────────────────

frappe.ui.form.on("ESS Workflow Settings", {
	refresh(frm) {
		frm.fields_dict["ess_workflow_documents"].grid.get_field("document").get_query =
			() => ({
				query: "employee_self_service.employee_self_service.doctype.ess_workflow_settings.ess_workflow_settings.get_workflow_doctypes",
			});

		frm.add_custom_button(__("Fetch Workflow Documents"), () => {
			frappe.call({
				method: "employee_self_service.employee_self_service.doctype.ess_workflow_settings.ess_workflow_settings.fetch_all_workflow_documents",
				freeze: true,
				freeze_message: __("Fetching active workflow documents…"),
				callback(r) {
					if (!r.message?.length) {
						frappe.msgprint({ title: __("No active workflows"), message: __("No active Workflow documents found."), indicator: "orange" });
						return;
					}
					const existing = (frm.doc.ess_workflow_documents || []).map(row => row.document);
					let added = 0;
					r.message.forEach(item => {
						if (existing.includes(item.document_type)) return;
						const row = frappe.model.add_child(frm.doc, "ESS Workflow Documents", "ess_workflow_documents");
						frappe.model.set_value(row.doctype, row.name, "document", item.document_type);
						frappe.model.set_value(row.doctype, row.name, "list_view_config", item.list_view_config);
						frappe.model.set_value(row.doctype, row.name, "detail_view_config", item.detail_view_config);
						added++;
					});
					frm.refresh_field("ess_workflow_documents");
					frappe.show_alert({
						message: added > 0
							? __("{0} document(s) added with default config. Save to persist.", [added])
							: __("All active workflow documents are already configured."),
						indicator: added > 0 ? "green" : "blue",
					});
					if (added) frm.dirty();
				},
			});
		});
	},
});

// ─── Child table ──────────────────────────────────────────────────────────────

frappe.ui.form.on("ESS Workflow Documents", {
	configure(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.document) {
			frappe.msgprint({ title: __("Select a Document"), message: __("Please select a Document before configuring."), indicator: "orange" });
			return;
		}
		open_configure_dialog(frm, cdt, cdn, row);
	},
});

// ─── Configure dialog ─────────────────────────────────────────────────────────

function open_configure_dialog(frm, cdt, cdn, row) {
	_inject_css();

	frappe.call({
		method: "employee_self_service.employee_self_service.doctype.ess_workflow_settings.ess_workflow_settings.get_doctype_fields",
		args: { doctype: row.document },
		callback(r) {
			if (!r.message) return;

			const meta_fields = r.message;

			let existing_list   = {};
			let existing_detail = {};
			try { existing_list   = JSON.parse(row.list_view_config   || "{}"); } catch (e) {}
			try { existing_detail = JSON.parse(row.detail_view_config || "{}"); } catch (e) {}

			const list_state = { fields: (existing_list.fields || []).map(f => ({ ...f })) };
			const detail_state = {
				sections: (existing_detail.sections || [{ label: "Overview", fields: [] }]).map(s => ({
					label: s.label,
					id: _uid(),
					fields: (s.fields || []).map(f => ({ ...f, _id: _uid() })),
				})),
			};

			const dialog = new frappe.ui.Dialog({
				title: __("Configure: {0}", [row.document]),
				size: "extra-large",
				fields: [
					{ fieldtype: "Section Break", label: __("List View") },
					{ fieldname: "list_builder",   fieldtype: "HTML", options: "<div class='ess-list-root'></div>" },
					{ fieldtype: "Section Break", label: __("Detail View") },
					{ fieldname: "detail_builder", fieldtype: "HTML", options: "<div class='ess-detail-root'></div>" },
				],
				primary_action_label: __("Save Configuration"),
				primary_action() {
					const lc_fields = list_state.fields.filter(f => f.fieldname);
					if (!lc_fields.some(f => f.fieldname === "workflow_state")) {
						lc_fields.push({ fieldname: "workflow_state", label: "Status", fieldtype: "Data", is_badge: 1, slot: "status" });
					}

					const detail_config = {
						sections: detail_state.sections
							.map(s => ({
								label: s.label || "General",
								fields: s.fields.filter(f => f.fieldname).map(({ _id, ...rest }) => rest),
							}))
							.filter(s => s.fields.length),
					};

					frappe.model.set_value(cdt, cdn, "list_view_config",   JSON.stringify({ fields: lc_fields }));
					frappe.model.set_value(cdt, cdn, "detail_view_config", JSON.stringify(detail_config));
					dialog.hide();
					frappe.show_alert({ message: __("{0} configured successfully", [row.document]), indicator: "green" });
					frm.dirty();
				},
			});

			dialog.show();

			const list_root   = dialog.fields_dict.list_builder.$wrapper.find(".ess-list-root")[0];
			const detail_root = dialog.fields_dict.detail_builder.$wrapper.find(".ess-detail-root")[0];

			render_list_builder(list_root, meta_fields, list_state);
			render_detail_builder(detail_root, meta_fields, detail_state);
		},
	});
}

// ─── List View Builder ────────────────────────────────────────────────────────

function render_list_builder(root, meta_fields, state) {
	const MAX = 6;
	const SLOT_OPTIONS = [
		{ value: "id",     label: "ID" },
		{ value: "status", label: "Status" },
		{ value: "body",   label: "Body" },
		{ value: "footer", label: "Footer" },
	];
	const default_slot = fname => {
		if (fname === "name") return "id";
		if (fname === "workflow_state") return "status";
		return "body";
	};

	root.innerHTML = `
		<div class="ess-cfg" style="margin-top:10px">
			<div class="ess-fill-row" id="lv-fill-row"></div>
			<div class="ess-cfg-row" style="margin-top:10px">
				<div class="ess-cfg-col-avail">
					<div class="ess-panel">
						<div class="ess-panel-hdr">Available Fields</div>
						<div class="ess-search-wrap"><input class="ess-search" placeholder="Search…" id="lv-search"></div>
						<div class="ess-avail-chips" id="lv-chips"></div>
					</div>
				</div>
				<div class="ess-cfg-col-main">
					<div class="ess-panel">
						<div class="ess-panel-hdr">
							Selected Fields
							<span class="ess-slot-badge" id="lv-count">0 / ${MAX}</span>
						</div>
						<div class="ess-items-wrap" id="lv-items">
							<div class="ess-drop-hint" id="lv-hint">Click a field on the left to add it here</div>
						</div>
					</div>
				</div>
			</div>
		</div>`;

	const chips_el  = root.querySelector("#lv-chips");
	const items_el  = root.querySelector("#lv-items");
	const hint_el   = root.querySelector("#lv-hint");
	const count_el  = root.querySelector("#lv-count");
	const search_el = root.querySelector("#lv-search");

	const fill_row = root.querySelector("#lv-fill-row");
	_make_fill_btn(fill_row, "Fill from List View Fields", () => {
		const to_add = meta_fields.filter(f => f.in_list_view).slice(0, MAX - 1);
		state.fields = to_add.map(f => ({
			fieldname: f.fieldname, label: f.label, fieldtype: f.fieldtype,
			is_badge: f.fieldname === "workflow_state" ? 1 : 0,
			slot: default_slot(f.fieldname),
		}));
		if (!state.fields.some(f => f.fieldname === "workflow_state")) {
			state.fields.push({ fieldname: "workflow_state", label: "Status", fieldtype: "Data", is_badge: 1, slot: "status" });
		}
		render_items(); render_chips();
	});
	_make_fill_btn(fill_row, "Fill from Mandatory Fields", () => {
		const to_add = meta_fields.filter(f => f.reqd).slice(0, MAX - 1);
		state.fields = to_add.map(f => ({
			fieldname: f.fieldname, label: f.label, fieldtype: f.fieldtype,
			is_badge: f.fieldname === "workflow_state" ? 1 : 0,
			slot: default_slot(f.fieldname),
		}));
		if (!state.fields.some(f => f.fieldname === "workflow_state")) {
			state.fields.push({ fieldname: "workflow_state", label: "Status", fieldtype: "Data", is_badge: 1, slot: "status" });
		}
		render_items(); render_chips();
	});

	function render_chips(filter_txt = "") {
		chips_el.innerHTML = "";
		const used = new Set(state.fields.map(f => f.fieldname));
		meta_fields
			.filter(f => !filter_txt || f.fieldname.toLowerCase().includes(filter_txt) || f.label.toLowerCase().includes(filter_txt))
			.forEach(f => {
				const chip = document.createElement("div");
				chip.className = "ess-chip" + (used.has(f.fieldname) ? " ess-chip-used" : "");
				chip.dataset.fieldname = f.fieldname;
				chip.innerHTML = `<span>${_esc(f.label)}</span><span class="ess-chip-type">${_esc(f.fieldtype)}</span>`;
				chip.addEventListener("click", () => {
					if (state.fields.length >= MAX) {
						frappe.show_alert({ message: __("Maximum {0} fields allowed", [MAX]), indicator: "orange" });
						return;
					}
					if (used.has(f.fieldname)) return;
					state.fields.push({
						fieldname: f.fieldname, label: f.label, fieldtype: f.fieldtype,
						is_badge: f.fieldname === "workflow_state" ? 1 : 0,
						slot: default_slot(f.fieldname),
					});
					render_items(); render_chips();
				});
				chips_el.appendChild(chip);
			});
	}

	function render_items() {
		items_el.querySelectorAll(".ess-item").forEach(el => el.remove());
		hint_el.style.display = state.fields.length ? "none" : "block";
		count_el.textContent  = `${state.fields.length} / ${MAX}`;
		count_el.className    = "ess-slot-badge" + (state.fields.length >= MAX ? " warn" : "");

		state.fields.forEach((field, idx) => {
			if (!field.slot) field.slot = default_slot(field.fieldname);
			const item = document.createElement("div");
			item.className = "ess-item";
			item.draggable = true;
			item.dataset.idx = idx;
			const slot_opts = SLOT_OPTIONS.map(o => `<option value="${o.value}" ${field.slot === o.value ? "selected" : ""}>${o.label}</option>`).join("");
			item.innerHTML = `
				<span class="ess-drag-handle" title="Drag to reorder">⠿</span>
				<span class="ess-item-fname" title="${_esc(field.fieldname)}">${_esc(field.fieldname)}</span>
				<input class="ess-item-label" value="${_esc(field.label)}" placeholder="Display label">
				<select class="ess-item-slot" title="Position on card">${slot_opts}</select>
				<label class="ess-badge-lbl" title="Show as coloured badge">
					<input type="checkbox" ${field.is_badge ? "checked" : ""}> Badge
				</label>
				<button class="ess-remove-btn" title="Remove">×</button>`;

			item.querySelector(".ess-item-label").addEventListener("input", e => { state.fields[idx].label = e.target.value; });
			item.querySelector(".ess-item-slot").addEventListener("change", e => { state.fields[idx].slot = e.target.value; });
			item.querySelector("input[type=checkbox]").addEventListener("change", e => { state.fields[idx].is_badge = e.target.checked ? 1 : 0; });
			item.querySelector(".ess-remove-btn").addEventListener("click", () => {
				state.fields.splice(idx, 1);
				render_items(); render_chips();
			});

			item.addEventListener("dragstart", e => {
				e.dataTransfer.setData("text/plain", idx);
				setTimeout(() => item.classList.add("dragging"), 0);
			});
			item.addEventListener("dragend", () => item.classList.remove("dragging"));

			items_el.appendChild(item);
		});

		items_el.ondragover  = e => { e.preventDefault(); items_el.classList.add("drag-over"); };
		items_el.ondragleave = () => items_el.classList.remove("drag-over");
		items_el.ondrop = e => {
			e.preventDefault();
			items_el.classList.remove("drag-over");
			const from_idx = parseInt(e.dataTransfer.getData("text/plain"));
			const target   = e.target.closest(".ess-item");
			if (!target || isNaN(from_idx)) return;
			const to_idx = parseInt(target.dataset.idx);
			if (from_idx === to_idx) return;
			const [moved] = state.fields.splice(from_idx, 1);
			state.fields.splice(to_idx, 0, moved);
			render_items(); render_chips();
		};
	}

	search_el.addEventListener("input", e => render_chips(e.target.value.toLowerCase().trim()));

	render_chips();
	render_items();
}

// ─── Detail View Builder ──────────────────────────────────────────────────────

function render_detail_builder(root, meta_fields, state) {
	root.innerHTML = `
		<div class="ess-cfg" style="margin-top:10px">
			<div class="ess-fill-row" id="dv-fill-row"></div>
			<div class="ess-cfg-row" style="margin-top:10px">
				<div class="ess-cfg-col-avail">
					<div class="ess-panel">
						<div class="ess-panel-hdr">Available Fields</div>
						<div class="ess-search-wrap"><input class="ess-search" placeholder="Search…" id="dv-search"></div>
						<div class="ess-avail-chips" id="dv-chips"></div>
					</div>
				</div>
				<div class="ess-cfg-col-main">
					<div class="ess-sections-wrap" id="dv-sections"></div>
					<div class="ess-add-section" id="dv-add-section">＋ Add Section</div>
				</div>
			</div>
		</div>`;

	const chips_el    = root.querySelector("#dv-chips");
	const sections_el = root.querySelector("#dv-sections");
	const search_el   = root.querySelector("#dv-search");

	const fill_row = root.querySelector("#dv-fill-row");
	_make_fill_btn(fill_row, "Fill from Mandatory Fields", () => {
		const reqd       = meta_fields.filter(f => f.reqd);
		const reqd_names = new Set(reqd.map(f => f.fieldname));
		const prefix     = [];
		if (!reqd_names.has("name"))           prefix.push({ fieldname: "name",           label: "Document No", fieldtype: "Data", is_badge: 0 });
		if (!reqd_names.has("workflow_state")) prefix.push({ fieldname: "workflow_state", label: "Status",      fieldtype: "Data", is_badge: 1 });
		const all = [...prefix, ...reqd].map(f => ({
			fieldname: f.fieldname, label: f.label, fieldtype: f.fieldtype,
			is_badge: f.fieldname === "workflow_state" ? 1 : 0, _id: _uid(),
		}));
		if (!state.sections.length) state.sections.push({ id: _uid(), label: "Overview", fields: [] });
		state.sections[0].fields = all;
		render_sections(); render_chips();
	});

	function _used_fieldnames() {
		const s = new Set();
		state.sections.forEach(sec => sec.fields.forEach(f => s.add(f.fieldname)));
		return s;
	}

	function render_chips(filter_txt = "") {
		chips_el.innerHTML = "";
		const used = _used_fieldnames();
		meta_fields
			.filter(f => !filter_txt || f.fieldname.toLowerCase().includes(filter_txt) || f.label.toLowerCase().includes(filter_txt))
			.forEach(f => {
				const chip = document.createElement("div");
				chip.className = "ess-chip" + (used.has(f.fieldname) ? " ess-chip-used" : "");
				chip.draggable = !used.has(f.fieldname);
				chip.dataset.fieldname = f.fieldname;
				chip.dataset.label     = f.label;
				chip.dataset.fieldtype = f.fieldtype;
				chip.innerHTML = `<span>${_esc(f.label)}</span><span class="ess-chip-type">${_esc(f.fieldtype)}</span>`;

				chip.addEventListener("click", () => {
					if (used.has(f.fieldname)) return;
					const sec = state.sections[0] || _new_section(state);
					sec.fields.push({ fieldname: f.fieldname, label: f.label, fieldtype: f.fieldtype, is_badge: f.fieldname === "workflow_state" ? 1 : 0, _id: _uid() });
					render_sections(); render_chips();
				});

				chip.addEventListener("dragstart", e => {
					e.dataTransfer.setData("ess/chip", JSON.stringify({ fieldname: f.fieldname, label: f.label, fieldtype: f.fieldtype }));
				});

				chips_el.appendChild(chip);
			});
	}

	function render_sections() {
		sections_el.innerHTML = "";
		state.sections.forEach((sec, si) => {
			const sec_el = document.createElement("div");
			sec_el.className = "ess-section";
			sec_el.dataset.section_id = sec.id;
			sec_el.innerHTML = `
				<div class="ess-section-hdr">
					<input class="ess-section-name" value="${_esc(sec.label)}" placeholder="Section name">
					<button class="ess-remove-section" title="Remove section">×</button>
				</div>
				<div class="ess-section-items" id="si-${sec.id}"></div>`;

			sec_el.querySelector(".ess-section-name").addEventListener("input", e => { sec.label = e.target.value; });
			sec_el.querySelector(".ess-remove-section").addEventListener("click", () => {
				state.sections.splice(si, 1);
				render_sections(); render_chips();
			});

			const items_el = sec_el.querySelector(`#si-${sec.id}`);

			sec.fields.forEach((field, fi) => {
				items_el.appendChild(_make_detail_item(field, fi, sec, items_el, state, () => {
					render_sections(); render_chips();
				}));
			});

			items_el.addEventListener("dragover", e => { e.preventDefault(); items_el.classList.add("drag-over"); });
			items_el.addEventListener("dragleave", () => items_el.classList.remove("drag-over"));
			items_el.addEventListener("drop", e => {
				e.preventDefault();
				items_el.classList.remove("drag-over");

				const chip_data = e.dataTransfer.getData("ess/chip");
				if (chip_data) {
					const f = JSON.parse(chip_data);
					if (!_used_fieldnames().has(f.fieldname)) {
						sec.fields.push({ ...f, is_badge: f.fieldname === "workflow_state" ? 1 : 0, _id: _uid() });
						render_sections(); render_chips();
					}
					return;
				}

				const move_data = e.dataTransfer.getData("ess/item");
				if (move_data) {
					const { from_section_id, field_id } = JSON.parse(move_data);
					if (from_section_id === sec.id) return;
					const from_sec = state.sections.find(s => s.id === from_section_id);
					if (!from_sec) return;
					const fi_idx = from_sec.fields.findIndex(f => f._id === field_id);
					if (fi_idx === -1) return;
					const [moved_field] = from_sec.fields.splice(fi_idx, 1);
					sec.fields.push(moved_field);
					render_sections(); render_chips();
				}
			});

			if (!sec.fields.length) {
				const hint = document.createElement("div");
				hint.className = "ess-drop-hint";
				hint.textContent = "Click a field or drag it here";
				items_el.appendChild(hint);
			}

			sections_el.appendChild(sec_el);
		});
	}

	root.querySelector("#dv-add-section").addEventListener("click", () => {
		state.sections.push({ id: _uid(), label: `Section ${state.sections.length + 1}`, fields: [] });
		render_sections();
	});

	search_el.addEventListener("input", e => render_chips(e.target.value.toLowerCase().trim()));

	render_chips();
	render_sections();
}

// Makes a single field item inside a detail section
function _make_detail_item(field, fi, sec, items_el, state, refresh) {
	const item = document.createElement("div");
	item.className = "ess-item";
	item.draggable = true;
	item.dataset.field_id = field._id;
	item.innerHTML = `
		<span class="ess-drag-handle" title="Drag to reorder or move to another section">⠿</span>
		<span class="ess-item-fname" title="${_esc(field.fieldname)}">${_esc(field.fieldname)}</span>
		<input class="ess-item-label" value="${_esc(field.label)}" placeholder="Display label">
		<label class="ess-badge-lbl"><input type="checkbox" ${field.is_badge ? "checked" : ""}> Badge</label>
		<button class="ess-remove-btn" title="Remove">×</button>`;

	item.querySelector(".ess-item-label").addEventListener("input", e => { field.label = e.target.value; });
	item.querySelector("input[type=checkbox]").addEventListener("change", e => { field.is_badge = e.target.checked ? 1 : 0; });
	item.querySelector(".ess-remove-btn").addEventListener("click", () => {
		sec.fields.splice(fi, 1);
		refresh();
	});

	item.addEventListener("dragstart", e => {
		e.dataTransfer.setData("ess/item", JSON.stringify({ from_section_id: sec.id, field_id: field._id }));
		e.dataTransfer.setData("ess/item-reorder", JSON.stringify({ fi }));
		setTimeout(() => item.classList.add("dragging"), 0);
	});
	item.addEventListener("dragend", () => item.classList.remove("dragging"));
	item.addEventListener("dragover", e => {
		e.preventDefault();
		if (e.dataTransfer.types.includes("ess/item-reorder")) e.currentTarget.classList.add("drag-over");
	});
	item.addEventListener("dragleave", () => item.classList.remove("drag-over"));
	item.addEventListener("drop", e => {
		e.preventDefault();
		item.classList.remove("drag-over");
		const reorder_raw = e.dataTransfer.getData("ess/item-reorder");
		if (!reorder_raw) return;
		const { fi: from_fi } = JSON.parse(reorder_raw);
		if (from_fi === fi) return;
		const [moved] = sec.fields.splice(from_fi, 1);
		sec.fields.splice(fi, 0, moved);
		refresh();
	});

	return item;
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function _make_fill_btn(container, label, handler) {
	const btn = document.createElement("button");
	btn.className = "ess-fill-btn";
	btn.textContent = label;
	btn.addEventListener("click", handler);
	container.appendChild(btn);
}

function _new_section(state) {
	const sec = { id: _uid(), label: "Overview", fields: [] };
	state.sections.push(sec);
	return sec;
}

let _uid_counter = 0;
function _uid() { return "ess_" + Date.now() + "_" + (++_uid_counter); }

function _esc(str) {
	return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
