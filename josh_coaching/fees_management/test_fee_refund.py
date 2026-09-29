# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Functional tests for the fee refund flow: validation limits, invoice
adjustment on submit, and over-refund rejection. Run on a bench:

    bench --site <site> run-tests --app josh_coaching
"""

from __future__ import annotations

import frappe
from frappe.utils import nowdate

from josh_coaching.tests.testing import AcademyTestBase


class RefundTestBase(AcademyTestBase):
	def setUp(self):
		self.discipline = self.make_discipline()
		self.program = self.make_program(self.discipline)
		self.batch = self.make_batch(self.program)

	def _paid_invoice(self, first_name: str = "Refundee", amount: float = 1000) -> tuple:
		"""Submit an invoice and pay it in full; returns (student, invoice, payment)."""
		student = self.make_student(first_name)
		inv = self.make_submitted_invoice(student, amount=amount, due_date=nowdate())
		payment = frappe.get_doc(
			{
				"doctype": "Fee Payment",
				"student": student,
				"invoice": inv.name,
				"posting_date": nowdate(),
				"amount": amount,
				"mode_of_payment": "Cash",
			}
		)
		payment.insert(ignore_permissions=True)
		payment.submit()
		return student, inv, payment


class TestFeeRefund(RefundTestBase):
	def test_full_refund_reopens_invoice(self):
		student, inv, payment = self._paid_invoice("FullRefund")

		refund = frappe.get_doc(
			{
				"doctype": "Fee Refund",
				"student": student,
				"payment": payment.name,
				"amount": 1000,
				"reason": "Withdrawal",
				"refund_date": nowdate(),
				"mode_of_payment": "Cash",
				"adjust_outstanding": 1,
			}
		)
		refund.insert(ignore_permissions=True)
		refund.submit()

		self.assertEqual(refund.status, "Processed")
		inv.reload()
		self.assertEqual(inv.paid_amount, 0)
		self.assertEqual(inv.outstanding_amount, 1000)
		self.assertEqual(inv.status, "Unpaid")

	def test_partial_refund_leaves_partially_paid(self):
		student, inv, payment = self._paid_invoice("PartialRefund")

		refund = frappe.get_doc(
			{
				"doctype": "Fee Refund",
				"student": student,
				"payment": payment.name,
				"amount": 400,
				"reason": "Service Issue",
				"refund_date": nowdate(),
				"mode_of_payment": "Cash",
				"adjust_outstanding": 1,
			}
		)
		refund.insert(ignore_permissions=True)
		refund.submit()

		inv.reload()
		self.assertEqual(inv.paid_amount, 600)
		self.assertEqual(inv.outstanding_amount, 400)
		self.assertEqual(inv.status, "Partially Paid")

	def test_over_refund_rejected(self):
		student, _inv, payment = self._paid_invoice("OverRefund")

		refund = frappe.get_doc(
			{
				"doctype": "Fee Refund",
				"student": student,
				"payment": payment.name,
				"amount": 1200,
				"reason": "Other",
				"refund_date": nowdate(),
				"mode_of_payment": "Cash",
			}
		)
		with self.assertRaises(frappe.ThrowError):
			refund.insert(ignore_permissions=True)

	def test_refund_exceeding_prior_refunds_rejected(self):
		student, _inv, payment = self._paid_invoice("DoubleRefund")

		first = frappe.get_doc(
			{
				"doctype": "Fee Refund",
				"student": student,
				"payment": payment.name,
				"amount": 600,
				"reason": "Duplicate Payment",
				"refund_date": nowdate(),
				"mode_of_payment": "Cash",
			}
		)
		first.insert(ignore_permissions=True)
		first.submit()

		second = frappe.get_doc(
			{
				"doctype": "Fee Refund",
				"student": student,
				"payment": payment.name,
				"amount": 600,  # only 400 remains refundable
				"reason": "Other",
				"refund_date": nowdate(),
				"mode_of_payment": "Cash",
			}
		)
		with self.assertRaises(frappe.ThrowError):
			second.insert(ignore_permissions=True)

	def test_invoice_fields_copied_from_payment(self):
		student, inv, payment = self._paid_invoice("CopyFields")

		refund = frappe.get_doc(
			{
				"doctype": "Fee Refund",
				"student": student,
				"payment": payment.name,
				"amount": 100,
				"reason": "Other",
				"refund_date": nowdate(),
				"mode_of_payment": "Cash",
			}
		)
		refund.insert(ignore_permissions=True)
		self.assertEqual(refund.invoice, inv.name)
		self.assertEqual(refund.currency, "INR")
