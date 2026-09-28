# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SessionFeedback(Document):
	def validate(self):
		self.submitted_by = self.submitted_by or frappe.session.user
		self._single_feedback_per_session()

	def _single_feedback_per_session(self):
		exists = frappe.db.exists(
			"Session Feedback",
			{
				"class_session": self.class_session,
				"student": self.student,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(_("Feedback already submitted for this student in this session"))
