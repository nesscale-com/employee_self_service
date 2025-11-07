"""
Generic CRUD APIs for any DocType
"""

from employee_self_service.mobile.v1.generic_api.api import (
    get_list,
    get_details,
    create,
    update,
)

__all__ = ["get_list", "get_details", "create", "update"]
