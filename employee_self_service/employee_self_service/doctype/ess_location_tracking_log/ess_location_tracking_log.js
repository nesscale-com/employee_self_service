// Copyright (c) 2026, Nesscale Solutions Private Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("ESS Location Tracking Log", {
	refresh(frm) {
		render_location_map(frm);
	},
});

// Re-render whenever the log rows change.
frappe.ui.form.on("ESS Location Tracking Log Details", {
	log_details_add: (frm) => render_location_map(frm),
	log_details_remove: (frm) => render_location_map(frm),
	latitude: (frm) => render_location_map(frm),
	longitude: (frm) => render_location_map(frm),
	timestamp: (frm) => render_location_map(frm),
});

function render_location_map(frm) {
	const wrapper = frm.get_field("location_map").$wrapper;
	if (!wrapper) return;

	// Collect valid points and sort them chronologically so the trail and
	// timeline read in the order the locations were actually recorded.
	const points = (frm.doc.log_details || [])
		.map((row) => ({
			lat: parseFloat(row.latitude),
			lng: parseFloat(row.longitude),
			timestamp: row.timestamp,
		}))
		.filter((p) => !isNaN(p.lat) && !isNaN(p.lng))
		.sort((a, b) => {
			const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
			const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
			return ta - tb;
		});

	if (!points.length) {
		wrapper.html(
			`<div class="text-muted" style="padding: 15px 0;">
				${__("Add rows with latitude and longitude to see the location trail.")}
			</div>`
		);
		return;
	}

	// Layout: map on the left, scrollable timeline on the right.
	wrapper.html(`
		<div class="ess-location-tracker" style="display:flex; gap:15px; flex-wrap:wrap;">
			<div class="ess-map" style="flex:1 1 480px; min-width:300px; height:420px;
				border:1px solid var(--border-color); border-radius:var(--border-radius-md);"></div>
			<div class="ess-timeline" style="flex:1 1 280px; min-width:240px; height:420px;
				overflow-y:auto; border:1px solid var(--border-color);
				border-radius:var(--border-radius-md); padding:10px;"></div>
		</div>
	`);

	render_timeline(wrapper.find(".ess-timeline"), points);

	const map_el = wrapper.find(".ess-map").get(0);
	// The container often has no size on first paint inside a form section,
	// so defer map creation and invalidate its size once it is visible.
	setTimeout(() => draw_map(frm, map_el, points), 200);
}

function draw_map(frm, map_el, points) {
	if (!map_el || typeof L === "undefined") return;

	// Tear down any previous map instance bound to this element.
	if (frm._location_map) {
		frm._location_map.remove();
		frm._location_map = null;
	}

	const map = L.map(map_el);
	frm._location_map = map;

	L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
		attribution: "© OpenStreetMap contributors",
		maxZoom: 19,
	}).addTo(map);

	const latlngs = points.map((p) => [p.lat, p.lng]);

	// Connect the points in chronological order to show the movement path.
	L.polyline(latlngs, { color: "#2490ef", weight: 3, opacity: 0.8 }).addTo(map);

	points.forEach((p, i) => {
		const is_start = i === 0;
		const is_end = i === points.length - 1;
		const color = is_start ? "#28a745" : is_end ? "#e24c4c" : "#2490ef";
		const label = is_start ? __("Start") : is_end ? __("End") : i + 1;

		L.marker([p.lat, p.lng], {
			icon: L.divIcon({
				className: "ess-marker",
				html: `<div style="background:${color}; color:#fff; border-radius:50%;
					width:26px; height:26px; line-height:26px; text-align:center;
					font-size:11px; font-weight:600; border:2px solid #fff;
					box-shadow:0 0 3px rgba(0,0,0,0.4);">${label}</div>`,
				iconSize: [26, 26],
				iconAnchor: [13, 13],
			}),
		})
			.addTo(map)
			.bindPopup(
				`<b>${frappe.datetime.str_to_user(p.timestamp) || __("No timestamp")}</b><br>
				${p.lat.toFixed(6)}, ${p.lng.toFixed(6)}`
			);
	});

	map.fitBounds(L.latLngBounds(latlngs), { padding: [30, 30], maxZoom: 17 });
	map.invalidateSize();
}

function render_timeline($timeline, points) {
	const rows = points
		.map((p, i) => {
			const is_start = i === 0;
			const is_end = i === points.length - 1;
			const color = is_start ? "#28a745" : is_end ? "#e24c4c" : "#2490ef";
			const label = is_start ? __("Start") : is_end ? __("End") : i + 1;
			const when = p.timestamp
				? frappe.datetime.str_to_user(p.timestamp)
				: __("No timestamp");

			return `
				<div style="display:flex; gap:10px; padding:8px 0;
					border-bottom:1px solid var(--border-color);">
					<div style="flex:0 0 24px; height:24px; line-height:24px; text-align:center;
						background:${color}; color:#fff; border-radius:50%;
						font-size:11px; font-weight:600;">${label}</div>
					<div>
						<div style="font-weight:600;">${when}</div>
						<div class="text-muted" style="font-size:12px;">
							${p.lat.toFixed(6)}, ${p.lng.toFixed(6)}
						</div>
					</div>
				</div>`;
		})
		.join("");

	$timeline.html(
		`<div style="font-weight:600; margin-bottom:8px;">
			${__("Timeline")} (${points.length})
		</div>${rows}`
	);
}
