# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class CoachingEvent(Document):
	def validate(self):
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("End Date cannot be before Start Date"))
		self.registered_count = frappe.db.count(
			"Event Participant", {"event": self.name, "status": ["!=", "Cancelled"]}
		)

	def on_update(self):
		if self.has_value_changed("status") and self.status == "Ongoing":
			frappe.msgprint(_("Remember to mark attendance for participants."))
