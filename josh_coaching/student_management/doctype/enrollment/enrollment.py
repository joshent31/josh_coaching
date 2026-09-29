# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, date_diff, getdate, nowdate, today

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


def get_frozen_enrollments() -> list[str]:
	"""Enrollment names currently frozen (excluded from auto-billing)."""
	return frappe.get_all(
		"Enrollment",
		filters={"freeze_status": "Frozen", "docstatus": 1},
		pluck="name",
	)


class Enrollment(Document):
	STATUS_WORKFLOW_MAP = STATUS_WORKFLOW_MAP

	def validate(self):
		self.validate_freeze_dates()
		self.validate_capacity()
		if self.freeze_status != "Frozen":
			self.set_next_billing_date()

	def validate_freeze_dates(self):
		if self.freeze_status == "Frozen":
			if not self.frozen_from:
				frappe.throw(_("Frozen From date is required to freeze an enrollment"))
			if self.frozen_to and getdate(self.frozen_to) < getdate(self.frozen_from):
				frappe.throw(_("Frozen To cannot be before Frozen From"))

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

	@frappe.whitelist()
	def freeze(self, frozen_from: str, frozen_to: str | None = None, reason: str | None = None):
		"""Pause this enrollment: skipped by auto-billing and attendance reminders."""
		self.freeze_status = "Frozen"
		self.frozen_from = frozen_from
		self.frozen_to = frozen_to
		self.freeze_reason = reason
		if self.docstatus == 0:
			self.save(ignore_permissions=True)
		else:
			from josh_coaching.utils import save_submitted

			save_submitted(self)
		return self.name

	@frappe.whitelist()
	def unfreeze(self):
		"""Resume billing: shift next_billing_date by the frozen duration."""
		shifted = None
		if self.frozen_from and self.next_billing_date:
			end = self.frozen_to or today()
			days = max(date_diff(end, self.frozen_from), 0)
			if days:
				shifted = add_days(self.next_billing_date, days)
				self.next_billing_date = shifted
		self.freeze_status = None
		self.frozen_from = None
		self.frozen_to = None
		self.freeze_reason = None
		if self.docstatus == 0:
			self.save(ignore_permissions=True)
		else:
			from josh_coaching.utils import save_submitted

			save_submitted(self)
		return shifted

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		try:
			from josh_coaching.student_management.waitlist_entry import (
				auto_promote_on_seat,
			)

			auto_promote_on_seat()
		except Exception:  # noqa: BLE001
			frappe.log_error(message=frappe.get_traceback(), title="Waitlist promotion failed")
