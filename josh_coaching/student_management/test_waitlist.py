# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Functional tests for waitlist positioning, promotion, and seat-filling
auto-promotion. Run on a bench:

    bench --site <site> run-tests --app josh_coaching
"""

from __future__ import annotations

import frappe
from frappe.utils import nowdate

from josh_coaching.tests.testing import AcademyTestBase


class WaitlistTestBase(AcademyTestBase):
	def setUp(self):
		self.discipline = self.make_discipline()
		self.program = self.make_program(self.discipline)

	def _batch_with_seats(self, max_seats: int = 2) -> str:
		return self.make_batch(self.program, max_seats=max_seats)

	def _add_waitlist(self, student: str, batch: str) -> object:
		entry = frappe.get_doc(
			{
				"doctype": "Waitlist Entry",
				"student": student,
				"program": self.program,
				"batch": batch,
				"joined_on": nowdate(),
			}
		)
		entry.insert(ignore_permissions=True)
		return entry


class TestWaitlistPositioning(WaitlistTestBase):
	def test_positions_assigned_in_join_order(self):
		batch = self._batch_with_seats()
		s1 = self.make_student("TEST-Wait1")
		s2 = self.make_student("TEST-Wait2")
		s3 = self.make_student("TEST-Wait3")

		e1 = self._add_waitlist(s1, batch)
		e2 = self._add_waitlist(s2, batch)
		e3 = self._add_waitlist(s3, batch)

		self.assertEqual(e1.position, 1)
		self.assertEqual(e2.position, 2)
		self.assertEqual(e3.position, 3)


class TestWaitlistPromotion(WaitlistTestBase):
	def test_promote_creates_enrollment_and_marks_promoted(self):
		batch = self._batch_with_seats()
		student = self.make_student("TEST-Promotee")
		entry = self._add_waitlist(student, batch)

		result = entry.promote()

		enrollment = frappe.get_doc("Enrollment", result["enrollment"])
		self.assertEqual(enrollment.student, student)
		self.assertEqual(enrollment.batch, batch)
		self.assertEqual(enrollment.docstatus, 0)
		entry.reload()
		self.assertEqual(entry.status, "Promoted")

	def test_promote_blocked_when_batch_full(self):
		batch = self._batch_with_seats(max_seats=1)
		seat_holder = self.make_student("TEST-SeatHolder")
		self.make_enrollment(seat_holder, self.program, batch, fee_plan=None)

		student = self.make_student("TEST-Blocked")
		entry = self._add_waitlist(student, batch)

		# capacity validation in Enrollment must reject the promotion
		with self.assertRaises(frappe.ThrowError):
			entry.promote()
		entry.reload()
		self.assertEqual(entry.status, "Waiting")

	def test_cancel_enrollment_auto_promotes_next_waiting(self):
		batch = self._batch_with_seats(max_seats=1)
		seat_holder = self.make_student("TEST-Leaver")
		enr = self.make_enrollment(seat_holder, self.program, batch, fee_plan=None)

		waiter = self.make_student("TEST-NextUp")
		self._add_waitlist(waiter, batch)

		# cancelling the active enrollment frees a seat -> auto promotion
		enr.cancel()

		self.assertTrue(
			frappe.db.exists(
				"Waitlist Entry", {"batch": batch, "student": waiter, "status": "Promoted"}
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"Enrollment", {"batch": batch, "student": waiter, "status": "Active"}
			)
		)
