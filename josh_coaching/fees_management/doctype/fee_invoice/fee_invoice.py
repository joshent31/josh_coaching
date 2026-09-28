# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, today


class FeeInvoice(Document):
	def validate(self):
		self.calculate_totals()
		if self.due_date and getdate(self.due_date) < getdate(self.posting_date):
			frappe.msgprint(_("Due Date is before Posting Date"))

	def calculate_totals(self):
		self.total_amount = sum(flt(d.amount) for d in self.items or [])
		self.tax_amount = flt(self.total_amount * flt(self.tax_rate or 0) / 100, 2)
		self.grand_total = flt(self.total_amount + (self.tax_amount or 0), 2)

	def before_submit(self):
		if not self.items:
			frappe.throw(_("Invoice has no line items"))

	def on_submit(self):
		self.db_set("status", "Unpaid")
		apply_customer_advance(self)
		try:
			from josh_coaching.notifications import notify_fee_due

			notify_fee_due(self)
		except Exception:  # noqa: BLE001 — notification must not block invoicing
			frappe.log_error(message=frappe.get_traceback(), title="Fee due notification failed")

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def update_payment_status(self):
		"""Recompute paid/outstanding after a Fee Payment is booked."""
		paid = flt(
			frappe.db.sql(
				"""SELECT COALESCE(SUM(amount), 0)
				FROM `tabFee Payment`
				WHERE invoice = %(invoice)s AND docstatus = 1""",
				{"invoice": self.name},
			)[0][0]
		)
		self.paid_amount = paid
		self.outstanding_amount = flt(self.total_amount) - paid
		if self.outstanding_amount <= 0:
			self.status = "Paid"
		elif paid > 0:
			self.status = "Partially Paid"
		else:
			self.status = "Unpaid"
		if self.status != "Overdue" and self.outstanding_amount > 0 and self.due_date and getdate(self.due_date) < getdate(today()):
			self.status = "Overdue"
		self.save(ignore_permissions=True)

	def make_sales_invoice(self, submit: bool = False):
		"""Realize revenue in ERPNext: create a Sales Invoice from this fee invoice."""
		if self.sales_invoice:
			frappe.throw(_("Sales Invoice {0} already exists").format(self.sales_invoice))

		customer = _get_or_create_customer(self.student)
		si = frappe.new_doc("Sales Invoice")
		si.customer = customer
		si.coaching_fee_invoice = self.name
		si.set_posting_time = 1
		si.posting_date = self.posting_date
		si.due_date = self.due_date
		si.currency = self.currency
		for row in self.items:
			si.append(
				"items",
				{
					"item_code": frappe.db.get_value("Fee Component", row.fee_component, "item"),
					"item_name": row.fee_component_name or row.fee_component,
					"qty": 1,
					"rate": row.amount,
					"coaching_fee_component": row.fee_component,
				},
			)
		si.insert(ignore_permissions=True)
		if submit:
			si.submit()
		self.db_set("sales_invoice", si.name)
		return si.name


def _get_or_create_customer(student: str) -> str:
	"""Map a Student to an ERPNext Customer (created on first use)."""
	existing = frappe.db.get_value("Sales Invoice", {"coaching_fee_invoice": student}, "customer")
	if existing:
		return existing

	customer_name = frappe.db.get_value("Customer", {"coaching_student": student})
	if customer_name:
		return customer_name

	student_doc = frappe.get_doc("Student", student)
	customer = frappe.new_doc("Customer")
	customer.customer_name = f"{student_doc.student_name} ({student_doc.student_id or student})"
	customer.customer_type = "Individual"
	customer.customer_group = customer.customer_group or "All Customer Groups"
	customer.territory = customer.territory or "All Territories"
	customer.coaching_student = student
	customer.insert(ignore_permissions=True)
	return customer.name


def apply_customer_advance(doc, method=None):
	"""Hook target (on_submit) — mark Unpaid; status transitions to
	Partially Paid / Paid as Fee Payments are submitted."""


def daily_overdue_escalation():
	"""Daily job: flag overdue invoices and notify managers past escalation days."""
	escalation_days = cint(
		frappe.db.get_single_value("Coaching Settings", "overdue_escalation_days") or 7
	)
	cutoff = add_days(today(), -escalation_days)

	overdue = frappe.get_all(
		"Fee Invoice",
		filters={
			"docstatus": 1,
			"status": ["in", ["Unpaid", "Partially Paid"]],
			"due_date": ["<", today()],
		},
		pluck="name",
	)
	for name in overdue:
		frappe.db.set_value("Fee Invoice", name, "status", "Overdue")

	escalate = frappe.get_all(
		"Fee Invoice",
		filters={
			"docstatus": 1,
			"status": "Overdue",
			"due_date": ["<", cutoff],
		},
		pluck="name",
	)
	if escalate:
		from josh_coaching.setup.batches import _notify_managers

		_notify_managers(
			subject=_("{0} fee invoices need escalation").format(len(escalate)),
			message=_(
				"{0} invoices are more than {1} days overdue: {2}"
			).format(len(escalate), escalation_days, ", ".join(escalate[:10])),
			user=None,
		)
	return len(overdue)
