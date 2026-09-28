# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, nowdate

STATUS_WORKFLOW_MAP = {
	"Draft": "Draft",
	"Active": "Active",
	"Completed": "Completed",
	"Withdrawn": "Withdrawn",
	"Cancelled": "Cancelled",
}

CYCLE_MONTHS = {
	"Monthly": 1,
	"Quarterly": 3,
	"Half-Yearly": 6,
	"Yearly": 12,
	"One-Time": 0,
}


class Enrollment(Document):
	STATUS_WORKFLOW_MAP = STATUS_WORKFLOW_MAP

	def validate(self):
		self.validate_capacity()
		self.set_next_billing_date()

	def before_submit(self):
		if not self.fee_plan:
			frappe.msgprint(_("No fee plan selected; no invoices will be generated."))

	def set_next_billing_date(self):
		months = CYCLE_MONTHS.get(self.billing_cycle, 1)
		base = self.start_date or self.enrollment_date or nowdate()
		if months:
			self.next_billing_date = add_months(base, months)
		else:
			self.next_billing_date = None

	def validate_capacity(self):
		batch = frappe.get_doc("Batch", self.batch)
		if batch.status in ("Completed", "Cancelled"):
			frappe.throw(_("Batch {0} is not open for enrollment").format(self.batch))
		existing = frappe.db.count(
			"Enrollment",
			{"batch": self.batch, "status": "Active", "docstatus": ["<", 2], "name": ["!=", self.name]},
		)
		max_seats = batch.max_seats or 0
		if max_seats and existing >= max_seats:
			frappe.throw(_("Batch {0} is full ({1}/{2} seats)").format(self.batch, existing, max_seats))

	def on_submit(self):
		self.db_set("status", "Active")
		frappe.db.commit()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
