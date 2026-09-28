# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FeeRefund(Document):
	def validate(self):
		payment = frappe.get_doc("Fee Payment", self.payment)
		if payment.docstatus != 1:
			frappe.throw(_("Payment {0} is not submitted").format(self.payment))
		self.student = payment.student
		self.currency = payment.currency
		if not self.invoice:
			self.invoice = payment.invoice

		refunded = self._already_refunded()
		refundable = flt(payment.amount) - refunded
		if flt(self.amount) > refundable:
			frappe.throw(
				_("Refund {0} exceeds refundable {1} on payment {2}").format(
					self.amount, refundable, self.payment
				)
			)

	def _already_refunded(self) -> float:
		return flt(
			frappe.db.sql(
				"""SELECT COALESCE(SUM(amount), 0) FROM `tabFee Refund`
				WHERE payment = %(p)s AND docstatus = 1 AND status = 'Processed'""",
				{"p": self.payment},
			)[0][0]
		)

	def on_submit(self):
		self.db_set("status", "Processed")
		if self.adjust_outstanding and self.invoice:
			invoice = frappe.get_doc("Fee Invoice", self.invoice)
			invoice.paid_amount = flt(invoice.paid_amount) + flt(self.amount)
			invoice.outstanding_amount = flt(invoice.grand_total or invoice.total_amount) - flt(invoice.paid_amount)
			if invoice.outstanding_amount <= 0:
				invoice.status = "Paid"
			elif flt(invoice.paid_amount) > 0:
				invoice.status = "Partially Paid"
			invoice.save(ignore_permissions=True)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
