# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class FeePayment(Document):
	def validate(self):
		if self.invoice:
			invoice = frappe.get_doc("Fee Invoice", self.invoice)
			if invoice.docstatus != 1:
				frappe.throw(_("Fee Invoice {0} is not submitted").format(self.invoice))
			if invoice.status in ("Paid", "Cancelled"):
				frappe.throw(_("Fee Invoice {0} is already {1}").format(self.invoice, invoice.status))
			outstanding = flt(invoice.total_amount) - flt(invoice.paid_amount)
			if flt(self.amount) > outstanding:
				frappe.throw(
					_("Amount {0} exceeds outstanding {1} for invoice {2}").format(
						self.amount, outstanding, self.invoice
					)
				)
			self.currency = invoice.currency
			self.student = invoice.student

	def before_submit(self):
		receipt = create_fee_receipt(self)
		self.db_set("fee_receipt", receipt.name)

	def on_submit(self):
		invoice = frappe.get_doc("Fee Invoice", self.invoice)
		invoice.update_payment_status()

	def on_cancel(self):
		invoice = frappe.get_doc("Fee Invoice", self.invoice)
		if invoice.docstatus == 1:
			invoice.update_payment_status()
		if self.fee_receipt:
			frappe.db.set_value("Fee Receipt", self.fee_receipt, "status", "Cancelled")


def create_fee_receipt(payment: Document) -> Document:
	receipt = frappe.new_doc("Fee Receipt")
	receipt.student = payment.student
	receipt.payment = payment.name
	receipt.invoice = payment.invoice
	receipt.amount = payment.amount
	receipt.currency = payment.currency
	receipt.mode_of_payment = payment.mode_of_payment
	receipt.posting_date = payment.posting_date or today()
	receipt.insert(ignore_permissions=True)
	return receipt
