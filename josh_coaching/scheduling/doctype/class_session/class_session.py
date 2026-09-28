# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ClassSession(Document):
	def validate(self):
		if not self.qr_token:
			self.generate_qr_token()
		if self.substitute_trainer and self.substitute_trainer == self.trainer:
			frappe.throw(_("Substitute Trainer must differ from the regular Trainer"))

	def generate_qr_token(self):
		"""Issue (or re-issue) the rotating token encoded in the session QR."""
		self.qr_token = frappe.generate_hash(length=24)
		self.qr_generated_at = now_datetime()

	def update_attendance_summary(self):
		summary = {"Present": 0, "Absent": 0, "Late": 0, "Excused": 0}
		for row in frappe.get_all(
			"Student Attendance",
			filters={"class_session": self.name},
			fields=["present"],
		):
			summary[row.present] = summary.get(row.present, 0) + 1
		self.attendance_summary = " / ".join(f"{k}: {v}" for k, v in summary.items())

	def on_update(self):
		self.update_attendance_summary()
