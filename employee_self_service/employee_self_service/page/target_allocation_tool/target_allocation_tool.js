frappe.pages['target-allocation-tool'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Target Allocation Tool'),
        single_column: true
    });

    // Add filter fields to the page
    page.from_date = page.add_field({
        fieldname: 'from_date',
        label: __('From Date'),
        fieldtype: 'Date',
        default: frappe.datetime.month_start(),
        reqd: 1,
        change: function () {
            page.target_entry.set_value('');
            page.clear_results();
        }
    });

    page.to_date = page.add_field({
        fieldname: 'to_date',
        label: __('To Date'),
        fieldtype: 'Date',
        default: frappe.datetime.get_today(),
        reqd: 1,
        change: function () {
            page.target_entry.set_value('');
            page.clear_results();
        }
    });

    page.employee = page.add_field({
        fieldname: 'employee',
        label: __('Employee'),
        fieldtype: 'Link',
        options: 'Employee',
        reqd: 1,
        get_query: function () {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        },
        change: function () {
            page.target_entry.set_value('');
            page.update_target_filter();
            page.clear_results();
        }
    });

    page.target_entry = page.add_field({
        fieldname: 'target_entry',
        label: __('Target Entry'),
        fieldtype: 'Link',
        options: 'Employee Target Entry',
        reqd: 1,
        get_query: function () {
            if (page.employee.get_value() && page.from_date.get_value() && page.to_date.get_value()) {
                return {
                    filters: {
                        'employee': page.employee.get_value(),
                        'start_date': ['<=', page.to_date.get_value()],
                        'end_date': ['>=', page.from_date.get_value()]
                    }
                };
            }
            return {};
        },
        change: function () {
            page.clear_results();
        }
    });

    // Add Get Details button
    page.add_inner_button(__('Get Transaction Details'), function () {
        page.get_transaction_details();
    }).addClass('btn-primary');

    // Helper functions
    page.update_target_filter = function () {
        if (page.target_entry) {
            page.target_entry.refresh();
        }
    };

    page.clear_results = function () {
        page.main.find('.transaction-results').remove();
    };

    page.get_transaction_details = function () {
        if (!page.employee.get_value() || !page.from_date.get_value() || !page.to_date.get_value() || !page.target_entry.get_value()) {
            frappe.msgprint(__('Please fill all mandatory fields: Employee, From Date, To Date, and Target Entry'));
            return;
        }

        frappe.call({
            method: 'employee_self_service.employee_self_service.page.target_allocation_tool.target_allocation_tool.get_sales_transactions',
            args: {
                employee: page.employee.get_value(),
                from_date: page.from_date.get_value(),
                to_date: page.to_date.get_value(),
                target_entry: page.target_entry.get_value()
            },
            callback: function (r) {
                if (r.message) {
                    page.render_transaction_table(r.message);
                }
            }
        });
    };

    page.render_transaction_table = function (data) {
        page.clear_results();

        if (!data || data.length === 0) {
            $(`<div class="transaction-results">
                <div class="alert alert-info">
                    <strong>No transactions found</strong> for the selected criteria.
                </div>
            </div>`).appendTo(page.main);
            return;
        }

        let html = `
            <div class="transaction-results" style="margin-top: 20px;">
                <h5>Transaction Details</h5>
                <div class="table-responsive">
                    <table class="table table-bordered table-striped">
                        <thead>
                            <tr>
                                <th>Document Type</th>
                                <th>Document No</th>
                                <th>Date</th>
                                <th>Customer</th>
                                <th>Total Amount</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        data.forEach(function (row) {
            let statusBadge = '';
            let actionButton = '';

            if (row.is_allocated) {
                statusBadge = '<span class="badge badge-success">Allocated</span>';
                actionButton = `<button class="btn btn-sm btn-warning unallocate-btn"
                                       data-doctype="${row.doctype}"
                                       data-docname="${row.name}"
                                       data-target-log="${row.allocated_target || ''}">
                                   Unallocate
                               </button>`;
            } else {
                statusBadge = '<span class="badge badge-warning">Not Allocated</span>';
                actionButton = `<button class="btn btn-sm btn-primary allocate-btn"
                                       data-doctype="${row.doctype}"
                                       data-docname="${row.name}">
                                   Allocate
                               </button>`;
            }

            html += `
                <tr>
                    <td>${row.doctype}</td>
                    <td><a href="/app/${row.doctype.toLowerCase().replace(' ', '-')}/${row.name}" target="_blank">${row.name}</a></td>
                    <td>${frappe.datetime.str_to_user(row.transaction_date)}</td>
                    <td>${row.customer_name}</td>
                    <td>${format_currency(row.grand_total)}</td>
                    <td>${statusBadge}</td>
                    <td>${actionButton}</td>
                </tr>
            `;
        });

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        $(html).appendTo(page.main);

        // Bind allocation button events
        page.main.find('.allocate-btn').on('click', function () {
            let doctype = $(this).data('doctype');
            let docname = $(this).data('docname');
            page.allocate_transaction(doctype, docname);
        });

        // Bind unallocation button events
        page.main.find('.unallocate-btn').on('click', function () {
            let doctype = $(this).data('doctype');
            let docname = $(this).data('docname');
            let targetLog = $(this).data('target-log');
            page.unallocate_transaction(doctype, docname, targetLog);
        });
    };

    page.allocate_transaction = function (doctype, docname) {
        if (!page.target_entry.get_value()) {
            frappe.msgprint(__('Please select a Target Entry first'));
            return;
        }

        frappe.confirm(
            __('Are you sure you want to allocate {0} <strong>{1}</strong> to the selected target?', [doctype, docname]),
            function () {
                frappe.call({
                    method: 'employee_self_service.employee_self_service.page.target_allocation_tool.target_allocation_tool.allocate_transaction_to_target',
                    args: {
                        employee: page.employee.get_value(),
                        target_entry: page.target_entry.get_value(),
                        doc_type: doctype,
                        doc_name: docname
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'green'
                            });
                            // Refresh the table
                            page.get_transaction_details();
                        }
                    }
                });
            }
        );
    };

    page.unallocate_transaction = function (doctype, docname, targetLog) {
        frappe.confirm(
            __('Are you sure you want to unallocate {0} <strong>{1}</strong>? This will cancel the target log.', [doctype, docname]),
            function () {
                frappe.call({
                    method: 'employee_self_service.employee_self_service.page.target_allocation_tool.target_allocation_tool.unallocate_transaction',
                    args: {
                        doc_type: doctype,
                        doc_name: docname
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'orange'
                            });
                            // Refresh the table
                            page.get_transaction_details();
                        }
                    }
                });
            }
        );
    };
};