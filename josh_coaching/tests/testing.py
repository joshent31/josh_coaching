# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Shared helpers for josh_coaching functional tests.

Every helper creates documents prefixed with ``TEST-`` so cleanup can find
and remove them. FrappeTestCase rolls back after each test, so this is a
safety net for committed documents (auto-billing calls frappe.db.commit()).
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate, random_string

CLEANUP_ORDER = (
	("Fee Refund", {"student": ["like", "TEST-%"]}),
	("Fee Receipt", {"student": ["like", "TEST-%"]}),
	("Fee Payment", {"student": ["like", "TEST-%"]}),
	("Fee Invoice", {"student": ["like", "TEST-%"]}),
	("Student Attendance", {"student": ["like", "TEST-%"]}),
	("Class Session", {"name": ["like", "%"]}),
	("Session Pack", {"student": ["like", "TEST-%"]}),
	("Makeup Credit", {"student": ["like", "TEST-%"]}),
	("Waitlist Entry", {"student": ["like", "TEST-%"]}),
	("Enrollment", {"student": ["like", "TEST-%"]}),
	("Fee Plan", {"plan_name": ["like", "TEST-%"]}),
	("Fee Component", {"component_name": ["like", "TEST-%"]}),
	("Batch", {"batch_name": ["like", "TEST-%"]}),
	("Program", {"program_name": ["like", "TEST-%"]}),
	("Student", {"first_name": ["like", "TEST-%"]}),
	("Sports Discipline", {"discipline_name": ["like", "TEST-%"]}),
)


def cleanup_test_records():
	"""Delete TEST- records (cancel submitted docs first where needed)."""
	for doctype, filters in CLEANUP_ORDER:
		try:
			for name in frappe.get_all(doctype, filters=filters, pluck="name"):
				try:
					doc = frappe.get_doc(doctype, name)
					if doc.docstatus == 1:
						doc.cancel()
					frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
				except Exception:  # noqa: BLE001, S110 — best-effort cleanup
					pass
		except Exception:  # noqa: BLE001, S110 — table may not exist yet
			pass
	frappe.db.commit()


class AcademyTestBase(FrappeTestCase):
	"""Base class: TEST- record cleanup + factory helpers."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cleanup_test_records()

	@classmethod
	def tearDownClass(cls):
		cleanup_test_records()

	# -- factories ------------------------------------------------------
	def make_discipline(self) -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Sports Discipline",
				"discipline_name": f"TEST-Sport {random_string(6)}",
				"category": "Sports",
				"status": "Active",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def make_student(self, first_name: str, **kwargs) -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Student",
				"first_name": first_name,
				"last_name": "Tester",
				"guardian_name": f"{first_name} Guardian",
				"guardian_mobile": "+91 90000 00000",
				**kwargs,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def make_program(self, discipline: str) -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Program",
				"program_name": f"TEST-Program {random_string(6)}",
				"discipline": discipline,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def make_batch(self, program: str, max_seats: int = 5) -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_name": f"TEST-Batch {random_string(6)}",
				"program": program,
				"start_date": add_days(nowdate(), -30),
				"status": "Active",
				"max_seats": max_seats,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def make_fee_component(self, name: str | None = None) -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Fee Component",
				"component_name": name or f"TEST-Fee {random_string(6)}",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def make_fee_plan(self, amount: float, currency: str = "INR", component: str | None = None) -> str:
		plan = frappe.get_doc(
			{
				"doctype": "Fee Plan",
				"plan_name": f"TEST-Plan {random_string(6)}",
				"currency": currency,
				"billing_frequency": "Monthly",
				"components": [
					{"fee_component": component or self.make_fee_component(), "amount": amount}
				],
			}
		)
		plan.insert(ignore_permissions=True)
		return plan.name

	def make_enrollment(
		self, student: str, program: str, batch: str, fee_plan: str | None = None, **kwargs
	) -> object:
		doc = frappe.get_doc(
			{
				"doctype": "Enrollment",
				"student": student,
				"program": program,
				"batch": batch,
				"enrollment_date": add_days(nowdate(), -30),
				"billing_cycle": "Monthly",
				"fee_plan": fee_plan,
				**kwargs,
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
		return doc

	def make_class_session(self, batch: str, program: str, **kwargs) -> object:
		doc = frappe.get_doc(
			{
				"doctype": "Class Session",
				"batch": batch,
				"program": program,
				"session_date": nowdate(),
				"start_time": "18:00:00",
				"end_time": "19:00:00",
				"status": "In Progress",
				**kwargs,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def make_submitted_invoice(self, student: str, amount: float, due_date: str, enrollment: str | None = None, component: str | None = None) -> object:
		doc = frappe.get_doc(
			{
				"doctype": "Fee Invoice",
				"student": student,
				"enrollment": enrollment,
				"posting_date": add_days(nowdate(), -30),
				"due_date": due_date,
				"currency": "INR",
				"items": [{"fee_component": component or self.make_fee_component(), "amount": amount}],
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
		return doc
