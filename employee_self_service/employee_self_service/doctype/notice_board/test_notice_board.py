# Copyright (c) 2022, Nesscale Solutions Private Limited and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestNoticeBoard(FrappeTestCase):
    def test_make_notice_board(self):
        frappe.set_user("Administrator")
        doc = frappe.get_doc(
            dict(
                doctype="Notice Board",
                notice_title="Birthday",
                message="Test Message",
                from_date="2023-01-01",
                to_date="2023-01-31",
                apply_for="All Employee",
            )
        ).insert()
        print("Notice Board Test Finished")

    def test_second_function(self):
        print("Notice Board Test Finished 2")

    def testsecond_function(self):
        print("Notice Board Test Finished 3")
