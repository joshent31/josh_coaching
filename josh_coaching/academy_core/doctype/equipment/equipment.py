# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Equipment(Document):
	def validate(self):
		self.update_stock_counts()

	def update_stock_counts(self):
		self.issued_qty = frappe.db.count(
			"Equipment Issue",
			{"equipment": self.name, "status": "Issued"},
		)
		self.available_qty = (self.total_qty or 0) - self.issued_qty
