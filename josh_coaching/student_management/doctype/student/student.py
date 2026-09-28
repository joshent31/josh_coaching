# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

STATUS_WORKFLOW_MAP = {
	"Draft": "Draft",
	"Active": "Active",
	"Suspended": "Suspended",
	"Alumni": "Alumni",
	"Cancelled": "Cancelled",
}


class Student(Document):
	STATUS_WORKFLOW_MAP = STATUS_WORKFLOW_MAP

	def autoname(self):
		# format autoname keeps the generated name in self.name already;
		# mirror it into the card number when not supplied.
		if not self.student_id:
			self.student_id = self.name

	def validate(self):
		self.student_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
		if not self.qr_token:
			self.qr_token = frappe.generate_hash(length=20)
		self._validate_sibling()

	def _validate_sibling(self):
		"""Sibling link must be mutual and not self-referencing."""
		if not self.sibling:
			return
		if self.sibling == self.name:
			frappe.throw(_("A student cannot be their own sibling"))
		back = frappe.db.get_value("Student", self.sibling, "sibling")
		if back and back != self.name:
			frappe.throw(_("{0} is already linked as sibling of {1}").format(self.sibling, back))

	def on_update(self):
		if self.student_user and self.status == "Active":
			ensure_portal_user(self)

	def get_qr_payload(self) -> str:
		"""Payload encoded into the student's QR pass."""
		return f"JC-STUDENT:{self.student_id}:{self.qr_token}"


def ensure_portal_user(student: Document) -> str | None:
	"""Create (or link) a Website User for the student's guardian.

	Returns the user email. Invites with a password-less welcome mail when
	the account is new.
	"""
	if not student.student_user:
		return None

	if frappe.db.exists("User", student.student_user):
		user = frappe.get_doc("User", student.student_user)
	else:
		user = frappe.new_doc("User")
		user.update(
			{
				"email": student.student_user,
				"first_name": student.first_name,
				"last_name": student.last_name or student.guardian_name,
				"send_welcome_email": 1,
			}
		)
	user.user_type = "Website User"
	if "Student (Portal)" not in [r.role for r in user.get("roles", [])]:
		user.append("roles", {"role": "Student (Portal)"})
	user.flags.ignore_permissions = True
	user.save(ignore_permissions=True)
	return user.name
