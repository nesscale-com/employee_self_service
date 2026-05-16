frappe.listview_settings["Employee Details Update Request"] = {
    add_fields: ["status"],
    has_indicator_for_draft: 1,
    get_indicator: function (doc) {
        const status_color = {
            Pending: "orange",
            Approved: "green",
            Rejected: "red",
            Cancelled: "red",
        };
        return [__(doc.status), status_color[doc.status] || "grey", "status,=," + doc.status];
    },
};
