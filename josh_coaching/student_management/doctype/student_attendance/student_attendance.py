# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class StudentAttendance(Document):
	def validate(self):
		if not self.marked_by:
			self.marked_by = frappe.session.user
		if not self.batch and self.class_session:
			self.batch = frappe.db.get_value("Class Session", self.class_session, "batch")
		_duplicate_guard(self)

	def after_insert(self):
		self._touch_session()
		if self.present == "Absent":
			from josh_coaching.student_management.makeup_credit import issue_credit

			issue_credit(self.student, reason="Absent", attendance=self.name)

	def on_update(self):
		self._touch_session()

	def _touch_session(self):
		if self.class_session:
			try:
				session = frappe.get_doc("Class Session", self.class_session)
				session.update_attendance_summary()
				session.save(ignore_permissions=True)
			except frappe.DoesNotExistError:
				pass


def _duplicate_guard(doc: Document):
	"""One attendance record per student per session (or per day without session)."""
	filters = {
		"student": doc.student,
		"attendance_date": doc.attendance_date,
		"name": ["!=", doc.name],
	}
	if doc.class_session:
		filters["class_session"] = doc.class_session
	elif frappe.db.exists(
		"Student Attendance",
		{
			"student": doc.student,
			"attendance_date": doc.attendance_date,
			"name": ["!=", doc.name],
		},
	):
		frappe.throw(
			_("Attendance already marked for {0} on {1}").format(doc.student, doc.attendance_date)
		)
		return
	if doc.class_session and frappe.db.exists("Student Attendance", filters):
		frappe.throw(
			_("Attendance already marked for {0} in session {1}").format(doc.student, doc.class_session)
		)
