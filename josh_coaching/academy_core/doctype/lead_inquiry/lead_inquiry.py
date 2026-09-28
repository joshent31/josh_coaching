# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, today


class LeadInquiry(Document):
	def validate(self):
		if self.status == "Converted" and not self.converted_student:
			frappe.throw(_("Converted Student is required when status is Converted"))

	@frappe.whitelist()
	def convert_to_student(self, first_name: str, guardian_name: str, guardian_mobile: str,
			last_name: str | None = None, batch: str | None = None) -> dict:
		"""Create a Student (+ optional Enrollment) from this lead."""
		if self.status == "Converted":
			frappe.throw(_("Lead already converted"))

		student = frappe.new_doc("Student")
		student.first_name = first_name
		student.last_name = last_name
		student.student_mobile = self.mobile
		student.student_email = self.email
		student.guardian_name = guardian_name
		student.guardian_mobile = guardian_mobile
		student.status = "Active"
		student.insert(ignore_permissions=True)

		enrollment = None
		if batch:
			enrollment = frappe.new_doc("Enrollment")
			enrollment.student = student.name
			enrollment.program = self.interested_program
			enrollment.batch = batch
			enrollment.enrollment_date = today()
			enrollment.billing_cycle = "Monthly"
			enrollment.insert(ignore_permissions=True)

		self.status = "Converted"
		self.trial_status = "Converted"
		self.converted_student = student.name
		self.save(ignore_permissions=True)
		return {"student": student.name, "enrollment": enrollment.name if enrollment else None}


def notify_due_followups() -> int:
	"""Daily job: ping managers about leads with a follow-up due today/overdue."""
	due = frappe.get_all(
		"Lead Inquiry",
		filters={
			"status": ["in", ["New", "In Progress"]],
			"followup_date": ["<=", today()],
		},
		fields=["name", "lead_name", "mobile", "assigned_to"],
	)
	for lead in due:
		recipients = {lead.assigned_to} if lead.assigned_to else set()
		if cint(1):
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
					"subject": _("Lead follow-up due: {0}").format(lead.lead_name),
					"email_content": _("Lead {0} (mobile {1}) needs a follow-up call.").format(
						lead.lead_name, lead.mobile
					),
					"for_user": user,
					"type": "Reminder",
					"document_type": "Lead Inquiry",
					"document_name": lead.name,
				}
			).insert(ignore_permissions=True)
	return len(due)
