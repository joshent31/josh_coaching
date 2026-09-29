# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Functional tests for the auto-billing engine: recurring invoice
generation, sibling discount, and late-fee application. Run on a bench:

    bench --site <site> run-tests --app josh_coaching
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, add_months, getdate, nowdate

from josh_coaching.tests.testing import AcademyTestBase


class TestRecurringInvoices(AcademyTestBase):
	def setUp(self):
		self.discipline = self.make_discipline()
		self.program = self.make_program(self.discipline)
		self.batch = self.make_batch(self.program)

	def _enroll(self, first_name: str, amount: float = 2000, **enr_kwargs) -> object:
		student = self.make_student(first_name)
		plan = self.make_fee_plan(amount)
		enr = self.make_enrollment(student, self.program, self.batch, fee_plan=plan, **enr_kwargs)
		# next_billing_date is set to enrollment+1 month (in the future);
		# pull it into the auto-bill horizon so the engine picks it up.
		due = add_days(nowdate(), 2)
		frappe.db.set_value("Enrollment", enr.name, "next_billing_date", due, update_modified=False)
		enr.next_billing_date = due
		return enr

	def test_creates_invoice_for_due_enrollment(self):
		from josh_coaching.setup.billing import generate_recurring_invoices

		enr = self._enroll("Recurring", amount=2000)

		created = generate_recurring_invoices(days_ahead=5)
		self.assertEqual(len(created), 1)

		inv = frappe.get_doc("Fee Invoice", created[0])
		self.assertEqual(inv.student, enr.student)
		self.assertEqual(inv.enrollment, enr.name)
		self.assertEqual(inv.billing_period, getdate(enr.next_billing_date).strftime("%b %Y"))
		self.assertEqual(inv.total_amount, 2000)
		self.assertEqual(len(inv.items), 1)
		# billing date advanced one cycle
		new_next = frappe.db.get_value("Enrollment", enr.name, "next_billing_date")
		self.assertEqual(getdate(new_next), add_months(getdate(enr.next_billing_date), 1))

	def test_idempotent_one_invoice_per_period(self):
		from josh_coaching.setup.billing import generate_recurring_invoices

		enr = self._enroll("Idem", amount=1500)

		first = generate_recurring_invoices(days_ahead=5)
		self.assertEqual(len(first), 1)

		# second run in the same billing period must not create a duplicate
		second = generate_recurring_invoices(days_ahead=5)
		self.assertEqual(second, [])
		self.assertEqual(frappe.db.count("Fee Invoice", {"enrollment": enr.name}), 1)

	def test_skips_frozen_enrollments(self):
		from josh_coaching.setup.billing import generate_recurring_invoices

		enr = self._enroll("Frozen", amount=1200)
		enr.freeze(frozen_from=nowdate(), reason="Test freeze")

		created = generate_recurring_invoices(days_ahead=5)
		self.assertEqual(created, [])
		self.assertEqual(frappe.db.count("Fee Invoice", {"enrollment": enr.name}), 0)

	def test_skips_enrollments_without_fee_plan(self):
		from josh_coaching.setup.billing import generate_recurring_invoices

		student = self.make_student("NoPlan")
		self.make_enrollment(student, self.program, self.batch, fee_plan=None)

		created = generate_recurring_invoices(days_ahead=5)
		self.assertEqual(created, [])
		self.assertEqual(frappe.db.count("Fee Invoice", {"student": student}), 0)

	def test_discount_applied_to_line_amounts(self):
		from josh_coaching.setup.billing import generate_recurring_invoices

		enr = self._enroll("Discount", amount=1000, discount_percent=20)

		generate_recurring_invoices(days_ahead=5)
		inv = frappe.get_doc("Fee Invoice", {"enrollment": enr.name})
		self.assertEqual(inv.items[0].amount, 800)
		self.assertEqual(inv.total_amount, 800)


class TestSiblingDiscount(AcademyTestBase):
	def test_sibling_discount_applied_when_both_enrolled(self):
		from josh_coaching.setup.billing import (
			_effective_discount,
			generate_recurring_invoices,
		)

		discipline = self.make_discipline()
		program = self.make_program(discipline)
		batch = self.make_batch(program, max_seats=5)

		sib_a = self.make_student("TEST-SibA")
		sib_b = self.make_student("TEST-SibB", sibling=sib_a)
		frappe.db.set_value("Student", sib_a, "sibling", sib_b, update_modified=False)

		plan = self.make_fee_plan(2000)
		enr_a = self.make_enrollment(sib_a, program, batch, fee_plan=plan)
		self.make_enrollment(sib_b, program, batch, fee_plan=plan)

		# sibling discount (10%) kicks in because both are actively enrolled
		self.assertEqual(_effective_discount(enr_a), 10)

		due = add_days(nowdate(), 2)
		frappe.db.set_value("Enrollment", enr_a.name, "next_billing_date", due, update_modified=False)
		created = generate_recurring_invoices(days_ahead=5)

		inv = frappe.get_doc("Fee Invoice", created[0])
		self.assertEqual(inv.items[0].amount, 1800)

	def test_sibling_discount_ignored_when_sibling_not_enrolled(self):
		from josh_coaching.setup.billing import _effective_discount

		discipline = self.make_discipline()
		program = self.make_program(discipline)
		batch = self.make_batch(program)

		sib_a = self.make_student("TEST-SoloA")
		sib_b = self.make_student("TEST-SoloB", sibling=sib_a)
		frappe.db.set_value("Student", sib_a, "sibling", sib_b, update_modified=False)

		plan = self.make_fee_plan(2000)
		# only sib_a is enrolled; sib_b has no enrollment
		enr = self.make_enrollment(sib_a, program, batch, fee_plan=plan)
		self.assertEqual(_effective_discount(enr), 0)


class TestLateFees(AcademyTestBase):
	def setUp(self):
		self.late_component = self.make_fee_component(name="TEST-Late Fee")
		frappe.db.set_value(
			"Coaching Settings",
			None,
			{"late_fee_component": self.late_component, "late_fee_amount": 100},
			update_modified=False,
		)

	def _make_overdue_invoice(self, first_name: str = "LateFee") -> object:
		student = self.make_student(first_name)
		inv = self.make_submitted_invoice(student, amount=1000, due_date=add_days(nowdate(), -20))
		frappe.db.set_value("Fee Invoice", inv.name, "status", "Overdue", update_modified=False)
		return inv

	def test_late_fee_added_to_overdue_invoice(self):
		from josh_coaching.setup.billing import apply_late_fees

		inv = self._make_overdue_invoice()
		updated = apply_late_fees()
		self.assertIn(inv.name, updated)

		inv.reload()
		late_rows = [d for d in inv.items if d.fee_component == self.late_component]
		self.assertEqual(len(late_rows), 1)
		self.assertEqual(late_rows[0].amount, 100)
		self.assertEqual(inv.total_amount, 1100)
		self.assertEqual(inv.outstanding_amount, 1100)

	def test_late_fee_idempotent(self):
		from josh_coaching.setup.billing import apply_late_fees

		inv = self._make_overdue_invoice()
		apply_late_fees()
		updated_again = apply_late_fees()

		self.assertNotIn(inv.name, updated_again)
		inv.reload()
		self.assertEqual(
			len([d for d in inv.items if d.fee_component == self.late_component]), 1
		)

	def test_no_late_fee_when_unconfigured(self):
		from josh_coaching.setup.billing import apply_late_fees

		frappe.db.set_value(
			"Coaching Settings", None, {"late_fee_component": None}, update_modified=False
		)
		self.assertEqual(apply_late_fees(), [])
