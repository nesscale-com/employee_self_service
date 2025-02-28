// frappe.pages['employee-location-tracker'].on_page_load = function (wrapper) {
// 	var page = frappe.ui.make_app_page({
// 		parent: wrapper,
// 		title: 'Employee Location Tracker',
// 		single_column: true
// 	});
// }

frappe.pages['employee-location-tracker'].on_page_load = function (wrapper) {




	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Employee Location Tracker',
		single_column: true
	});

	// Create Filters
	const filters = {
		employee: page.add_field({
			fieldtype: 'Link',
			fieldname: 'employee',
			options: 'Employee',
			label: 'Employee',
			change: function () {
				load_map();
			}
		}),
		date: page.add_field({
			fieldtype: 'Date',
			fieldname: 'date',
			label: 'Date',
			change: function () {
				load_map();
			}
		})
	};

	// Create Map Container
	const mapDiv = $('<div id="map"></div>').appendTo(page.main);
	mapDiv.css({ height: '600px' });

	// Dynamically load Google Maps API
	loadGoogleMapsApi();

	// Dynamically load the Google Maps API script
	function loadGoogleMapsApi() {
		if (!window.google || !window.google.maps) {
			// Add Google Maps Script dynamically
			const script = document.createElement('script');
			script.src = "https://maps.googleapis.com/maps/api/js?key=AIzaSyDhKqaOvHzbVviz67ZPHjT3UEba2DNSzlw";
			script.async = true;
			script.defer = true;
			document.head.appendChild(script);
		} else {
			initMap([]); // Google Maps API is already loaded
		}
	}



	// Global function to initialize Google Maps
	window.initMap = function (locations = []) {
		if (locations.length > 0) {
			console.log(locations)
			console.log({ lat: locations[0].latitude, lng: locations[0].longitude })
			const map = new google.maps.Map(document.getElementById('map'), {
				zoom: 20,
				center: { lat: parseFloat(locations[0].latitude), lng: parseFloat(locations[0].longitude) }
			});
			const seq = {
				repeat: '50px',
				icon: {
					path: google.maps.SymbolPath.FORWARD_OPEN_ARROW,
					scale: 1,
					fillOpacity: 0,
					strokeColor: "white",
					strokeWeight: 1,
					strokeOpacity: 1,
				},
			};

			const flightPath = new google.maps.Polyline({
				path: locations.map(loc => ({ lat: parseFloat(loc.latitude), lng: parseFloat(loc.longitude) })),
				geodesic: true,
				zIndex: 1,
				strokeColor: '#00B3FD',
				strokeOpacity: 0.6,
				strokeWeight: 8,
				map: map,
				icons: [seq],
			});
		}
	};

	// Initialize Map with Google Maps API
	function load_map() {
		let employee = filters.employee.get_value();
		let date = filters.date.get_value();

		if (!employee || !date) {
			return;
		}

		// Get location data via Frappe API call
		frappe.call({
			method: 'employee_self_service.employee_self_service.page.employee_location_tracker.employee_location_tracker.get_employee_location',
			args: {
				employee: employee,
				date: date
			},
			callback: function (r) {
				if (r.message) {
					const locations = r.message;
					initMap(locations);
				}
			}
		});
	}

	// Initialize Google Maps with Arrow Markers
	// function initMap(locations) {
	// 	const map = new google.maps.Map(document.getElementById('map'), {
	// 		zoom: 10,
	// 		center: { lat: locations[0].latitude, lng: locations[0].longitude }
	// 	});

	// 	const seq = {
	// 		repeat: '50px',
	// 		icon: {
	// 			path: google.maps.SymbolPath.FORWARD_OPEN_ARROW,
	// 			scale: 1,
	// 			fillOpacity: 0,
	// 			strokeColor: "white",
	// 			strokeWeight: 1,
	// 			strokeOpacity: 1,
	// 		},
	// 	};

	// 	const flightPath = new google.maps.Polyline({
	// 		path: locations.map(loc => ({ lat: loc.latitude, lng: loc.longitude })),
	// 		geodesic: true,
	// 		zIndex: 1,
	// 		strokeColor: '#00B3FD',
	// 		strokeOpacity: 0.6,
	// 		strokeWeight: 8,
	// 		map: map,
	// 		icons: [seq],
	// 	});
	// }
};
