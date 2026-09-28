# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate

STATUS_WORKFLOW_MAP = {
	"Draft": "Draft",
	"Upcoming": "Upcoming",
	"Active": "Active",
	"Completed": "Completed",
	"Cancelled": "Cancelled",
}


class Batch(Document):
	STATUS_WORKFLOW_MAP = STATUS_WORKFLOW_MAP

	def validate(self):
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("End Date cannot be before Start Date"))
		if self.status == "Active" and not self.schedule:
			frappe.msgprint(_("Batch has no weekly schedule lines; generate sessions manually."))
		self.update_enrolled_count()

	def on_update(self):
		if self.has_value_changed("status") and self.status == "Active":
			frappe.enqueue(
				"josh_coaching.setup.batches.generate_sessions_for_batch",
				queue="short",
				batch=self.name,
				days_ahead=14,
			)

	def update_enrolled_count(self):
		self.enrolled_count = frappe.db.count(
			"Enrollment",
			{"batch": self.name, "status": "Active", "docstatus": 0},
		)
		if cint(self.max_seats) and self.enrolled_count > cint(self.max_seats):
			frappe.msgprint(
				_("Batch {0} is over capacity ({1}/{2})").format(
					self.name, self.enrolled_count, self.max_seats
				)
			)


def close_expired_batches():
	"""Daily job: complete Active batches past their end date."""
	from josh_coaching.setup.batches import close_expired_batches as _close

	_close()
