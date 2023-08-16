frappe.ui.form.on('Employee Checkin', {
	refresh(frm) {
		// your code here
		frm.add_custom_button("View Location",function(){
            window.open("https://www.google.com/maps/search/?api=1&query=" + frm.doc.location, '_blank');
		})
	}
})