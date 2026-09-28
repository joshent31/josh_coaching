# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from frappe.tests.utils import FrappeTestCase


class TestBilling(FrappeTestCase):
	def test_imports(self):
		"""Smoke test: billing engine imports cleanly on a bench."""
		from josh_coaching.setup import billing  # noqa: F401
