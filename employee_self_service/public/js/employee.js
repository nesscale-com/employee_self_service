frappe.ui.form.on('Employee', {
    refresh(frm) {
        // Only proceed if user has the required role
        if (frappe.user.has_role("HR User") || frappe.user.has_role("HR Manager") || frappe.user.has_role("System Manager")) {
            frappe.call({
                method: "employee_self_service.utils.is_device_button_enable",
                args: {
                    employee: frm.doc.name
                },
                callback: function (r) {
                    if (r.message) {
                        frm.add_custom_button(__("Clear Linked Device"), function () {
                            frappe.call({
                                method: "employee_self_service.utils.clear_linked_device",
                                args: { "employee": frm.doc.name },
                                callback: function (r) {
                                    frm.reload_doc()
                                    frappe.msgprint(__("Device registration cleared. Employee can now use a new device."))
                                }
                            })
                        });
                    }
                }
            });
        }
    }
});
