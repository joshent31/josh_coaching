# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class Announcement(Document):
	def on_submit(self):
		recipients = self._resolve_recipients()
		count = 0
		for user in recipients:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": self.title,
					"email_content": self.message,
					"for_user": user,
					"type": "Announcement",
					"document_type": "Announcement",
					"document_name": self.name,
				}
			).insert(ignore_permissions=True)
			count += 1
		self.db_set("recipients_notified", count)
		frappe.db.commit()

		if cint(self.send_whatsapp):
			self._send_gateway_messages()

	def _resolve_recipients(self) -> set[str]:
		recipients: set[str] = set()
		if self.audience_type == "All Students":
			student_names = frappe.get_all("Student", filters={"status": "Active"}, pluck="name")
		elif self.audience_type == "Selected Batches":
			batches = [row.batch for row in self.batches or []]
			student_names = frappe.get_all(
				"Enrollment", filters={"batch": ["in", batches], "status": "Active"}, pluck="student"
			)
		elif self.audience_type == "Selected Students":
			student_names = [row.student for row in self.students or []]
		else:  # All Trainers
			return set(frappe.get_all("Coach", filters={"status": "Active"}, pluck="user")) - {None}

		users = frappe.get_all(
			"Student",
			filters={"name": ["in", student_names or [""]], "student_user": ["is", "set"]},
			pluck="student_user",
		)
		recipients.update(users)
		recipients.discard(None)
		return recipients

	def _send_gateway_messages(self):
		from josh_coaching.notifications import send_sms, send_whatsapp

		bodies = []
		if self.audience_type == "All Students":
			student_names = frappe.get_all("Student", filters={"status": "Active"}, pluck="name")
		elif self.audience_type == "Selected Batches":
			batches = [row.batch for row in self.batches or []]
			student_names = frappe.get_all(
				"Enrollment", filters={"batch": ["in", batches], "status": "Active"}, pluck="student"
			)
		elif self.audience_type == "Selected Students":
			student_names = [row.student for row in self.students or []]
		else:
			return
		if student_names:
			bodies = frappe.get_all(
				"Student",
				filters={"name": ["in", student_names]},
				fields=["name", "guardian_mobile", "student_mobile"],
			)
		text = f"{self.title}\n{frappe.utils.strip_html(self.message)[:300]}"
		for row in bodies:
			for number in filter(None, [row.guardian_mobile, row.student_mobile]):
				if frappe.db.get_single_value("Coaching Settings", "whatsapp_gateway_url"):
					send_whatsapp(number, text, event="announcement")
				else:
					send_sms(number, text, event="announcement")
