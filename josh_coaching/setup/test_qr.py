# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Functional tests for the QR check-in engine: student payload resolution,
duplicate booking, window validation, and session-pack consumption. Run on a
bench:

    bench --site <site> run-tests --app josh_coaching
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime, nowdate

from josh_coaching.tests.testing import AcademyTestBase


class QRTestBase(AcademyTestBase):
	def setUp(self):
		self.discipline = self.make_discipline()
		self.program = self.make_program(self.discipline)
		self.batch = self.make_batch(self.program)

	def _student_with_session(self, first_name: str = "QRStudent", **enr_kwargs):
		student = self.make_student(first_name)
		self.make_enrollment(student, self.program, self.batch, fee_plan=None, **enr_kwargs)
		session = self.make_class_session(self.batch, self.program)
		return student, session


class TestStudentPayload(QRTestBase):
	def test_valid_student_qr_payload_resolves(self):
		from josh_coaching.setup.qr import check_in_student

		student, session = self._student_with_session()
		payload = frappe.db.get_value("Student", student, "qr_token")
		payload = f"JC-STUDENT:{student}:{payload}"
		# student_id mirrors the document name for format-named students
		result = check_in_student(payload, session=session.name)

		self.assertEqual(result["status"], "ok")
		self.assertTrue(frappe.db.exists(
			"Student Attendance",
			{"student": student, "class_session": session.name},
		))

	def test_bad_token_rejected(self):
		from josh_coaching.setup.qr import check_in_student

		student, session = self._student_with_session()
		payload = f"JC-STUDENT:{student}:forgedtoken123"

		with self.assertRaises(frappe.ThrowError):
			check_in_student(payload, session=session.name)

	def test_raw_student_id_fallback(self):
		from josh_coaching.setup.qr import check_in_student

		student, session = self._student_with_session("QRRaw")
		result = check_in_student(student, session=session.name, method="Manual")
		self.assertEqual(result["status"], "ok")


class TestCheckInRules(QRTestBase):
	def test_duplicate_checkin_returns_duplicate_status(self):
		from josh_coaching.setup.qr import check_in_student

		student, session = self._student_with_session("QRDup")
		first = check_in_student(student, session=session.name)
		self.assertEqual(first["status"], "ok")

		second = check_in_student(student, session=session.name)
		self.assertEqual(second["status"], "duplicate")

	def test_cancelled_session_rejects_checkin(self):
		from josh_coaching.setup.qr import check_in_student

		student, session = self._student_with_session("QRCancelled")
		session.status = "Cancelled"
		session.save(ignore_permissions=True)

		with self.assertRaises(frappe.ThrowError):
			check_in_student(student, session=session.name)

	def test_expired_qr_window_rejected(self):
		from josh_coaching.setup.qr import check_in_student

		student, session = self._student_with_session("QRExpired")
		# simulate a token generated 2 hours ago with a 15-minute window
		stale = frappe.utils.add_to_date(now_datetime(), hours=-2)
		frappe.db.set_value(
			"Class Session",
			session.name,
			{"qr_generated_at": stale, "checkin_window_minutes": 15},
			update_modified=False,
		)

		with self.assertRaises(frappe.ThrowError):
			check_in_student(student, session=session.name)

	def test_no_active_session_throws(self):
		from josh_coaching.setup.qr import check_in_student

		student = self.make_student("QRNoSession")
		# enroll in a batch with no session today
		self.make_enrollment(student, self.program, self.batch, fee_plan=None)

		with self.assertRaises(frappe.ThrowError):
			check_in_student(student)


class TestPackConsumption(QRTestBase):
	def test_checkin_consumes_session_pack(self):
		from josh_coaching.setup.qr import check_in_student

		student, session = self._student_with_session("QRPack")
		pack = frappe.get_doc(
			{
				"doctype": "Session Pack",
				"student": student,
				"pack_type": "10 Sessions",
				"total_sessions": 10,
				"purchase_date": nowdate(),
				"expires_on": add_days(nowdate(), 30),
				"status": "Active",
			}
		)
		pack.insert(ignore_permissions=True)

		check_in_student(student, session=session.name)

		pack.reload()
		self.assertEqual(pack.sessions_used, 1)
		self.assertEqual(pack.sessions_remaining, 9)
		self.assertEqual(pack.status, "Active")

	def test_exhausted_pack_marks_status(self):
		from josh_coaching.setup.qr import check_in_student

		student, session = self._student_with_session("QRLast")
		pack = frappe.get_doc(
			{
				"doctype": "Session Pack",
				"student": student,
				"pack_type": "10 Sessions",
				"total_sessions": 1,
				"sessions_used": 0,
				"purchase_date": nowdate(),
				"expires_on": add_days(nowdate(), 30),
				"status": "Active",
			}
		)
		pack.insert(ignore_permissions=True)

		check_in_student(student, session=session.name)

		pack.reload()
		self.assertEqual(pack.sessions_remaining, 0)
		self.assertEqual(pack.status, "Exhausted")
