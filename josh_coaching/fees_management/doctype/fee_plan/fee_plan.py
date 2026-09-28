# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class FeePlan(Document):
	def validate(self):
		self.total_amount = sum(flt(d.amount) for d in self.components or [])
