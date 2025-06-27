# from pos.admin_api.auth.auth_endpoints import auth_endpoints
# from pos.admin_api.masters.master_endpoints import master_endpoints
# from pos.admin_api.dashboard.dashboard_endpoints import dashboard_endpoints
# from pos.admin_api.modules.modules_endpoints import *


# def get_combined_endpoints():
#     """
#     Combines all endpoint dictionaries from different modules.
#     """
#     combined_endpoints = {}
#     modules = [
#         auth_endpoints,
#         master_endpoints,
#         pos_branch_endpoints,
#         pos_branch_settings_endpoints,
#         auth_endpoints,
#         customer_endpoints,
#         customer_group_endpoints,
#         item_endpoints,
#         item_group_endpoints,
#         order_endpoints,
#         pos_order_type_endpoints,
#         payment_mode_endpoints,
#         pos_session_endpoints,
#         user_endpoints,
#         pos_table_endpoints,
#         pos_modifiers_endpoints,
#         pos_sizes_endpoints,
#         warehouse_endpoints,
#         pos_translation_endpoints,
#         pos_attendance_endpoints,
#         price_list_endpoints,
#         address_endpoints,
#         pos_tag_endpoints,
#         coupon_code_endpoints,
#         pos_role_endpoints,
#         promotion_endpoints,
#         pos_order_endpoints,
#         pos_brand_endpoints,
#         loyalty_tier_endpoints,
#         loyalty_rule_endpoints,
#         loyalty_program_enrollment_endpoints,
#         loyalty_points_ledger_endpoints,
#         dashboard_endpoints,
#         pos_report_endpoints
#     ]

#     for module in modules:
#         combined_endpoints.update(module)

#     return combined_endpoints