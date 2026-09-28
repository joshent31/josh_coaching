# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class ParentCommunication(Document):
	def validate(self):
		if self.outcome in ("Resolved",) and self.status == "Open":
			self.status = "Closed"


def notify_due_followups() -> int:
	"""Daily job: remind assignees/managers about communications due today."""
	due = frappe.get_all(
		"Parent Communication",
		filters={
			"status": ["in", ["Open", "Waiting"]],
			"followup_date": ["<=", today()],
		},
		fields=["name", "subject", "student_name", "assigned_to"],
	)
	for comm in due:
		recipients = {comm.assigned_to} if comm.assigned_to else set()
		recipients.update(
			frappe.get_all(
				"Has Role",
				filters={"role": "Academy Manager", "parenttype": "User"},
				pluck="parent",
			)
		)
		recipients.discard(None)
		for user in recipients:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": _("Communication follow-up: {0}").format(comm.subject),
					"email_content": _("Follow up with {0}'s parents regarding \"{1}\".").format(
						comm.student_name or _("student"), comm.subject
					),
					"for_user": user,
					"type": "Reminder",
					"document_type": "Parent Communication",
					"document_name": comm.name,
				}
			).insert(ignore_permissions=True)
	return len(due)
