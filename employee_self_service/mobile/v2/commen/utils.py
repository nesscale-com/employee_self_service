import frappe
from frappe import _
from employee_self_service.mobile.v2.api_utils import *
from frappe.utils import *
from employee_self_service.utils import add_ess_comment
from frappe.handler import upload_file


def get_file_size(file_path, unit="auto"):
    file_size = os.path.getsize(file_path)

    units = ["B", "Kb", "Mb", "Gb", "Tb"]
    if unit == "auto":
        unit_index = 0
        while file_size > 1000:
            file_size /= 1000
            unit_index += 1
            if unit_index == len(units) - 1:
                break
        unit = units[unit_index]
    else:
        unit_index = units.index(unit)

    return f"{file_size:.2f}{unit}"
