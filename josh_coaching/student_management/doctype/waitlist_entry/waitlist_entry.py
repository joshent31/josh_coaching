# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class WaitlistEntry(Document):
	def validate(self):
		self.position = self._compute_position()

	def _compute_position(self) -> int:
		if self.status != "Waiting":
			return self.position or 0
		return frappe.db.count(
			"Waitlist Entry",
			{"batch": self.batch, "status": "Waiting", "name": ["!=", self.name]},
		) + 1

	@frappe.whitelist()
	def promote(self, enrollment_date: str | None = None) -> dict:
		"""Convert this waitlist entry into an Enrollment (seat is validated there)."""
		if self.status != "Waiting":
			frappe.throw(_("Only waiting entries can be promoted"))

		enrollment = frappe.new_doc("Enrollment")
		enrollment.student = self.student
		enrollment.program = self.program
		enrollment.batch = self.batch
		enrollment.enrollment_date = enrollment_date or today()
		enrollment.billing_cycle = "Monthly"
		enrollment.insert(ignore_permissions=True)

		self.status = "Promoted"
		self.save(ignore_permissions=True)
		return {"enrollment": enrollment.name}


def auto_promote_on_seat() -> int:
	"""Daily job + hook target: promote the first waiting entry when a batch has a free seat.

	Called from Enrollment.on_cancel / on withdraw to fill vacated seats.
	"""
	promoted = 0
	batches = frappe.get_all(
		"Waitlist Entry",
		filters={"status": "Waiting"},
		pluck="batch",
		distinct=True,
	)
	for batch in batches:
		# skip full batches
		frappe.get_doc("Batch", batch)  # ensure exists
		enrolled = frappe.db.count("Enrollment", {"batch": batch, "status": "Active", "docstatus": 1})
		max_seats = frappe.db.get_value("Batch", batch, "max_seats") or 0
		if max_seats and enrolled >= max_seats:
			continue
		entry = frappe.get_all(
			"Waitlist Entry",
			filters={"batch": batch, "status": "Waiting"},
			order_by="joined_on asc, creation asc",
			limit=1,
			pluck="name",
		)
		if entry:
			frappe.get_doc("Waitlist Entry", entry[0]).promote()
			promoted += 1
	return promoted
