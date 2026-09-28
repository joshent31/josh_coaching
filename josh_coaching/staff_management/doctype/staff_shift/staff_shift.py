# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class StaffShift(Document):
	def validate(self):
		if self.end_time <= self.start_time:
			frappe.throw(_("End Time must be after Start Time"))
		self._no_overlap()

	def _no_overlap(self):
		"""A trainer cannot have two overlapping shifts on the same day."""
		rows = frappe.get_all(
			"Staff Shift",
			filters={
				"trainer": self.trainer,
				"shift_date": self.shift_date,
				"status": "Planned",
				"name": ["!=", self.name],
			},
			fields=["name", "start_time", "end_time"],
		)
		for row in rows:
			if self.start_time < row.end_time and row.start_time < self.end_time:
				frappe.throw(
					_("Shift overlaps with {0} ({1} - {2})").format(
						row.name, row.start_time, row.end_time
					)
				)
