# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, now_datetime, today


class MakeupCredit(Document):
	def validate(self):
		if not self.expires_on and self.issued_on:
			validity = cint(
				frappe.db.get_single_value("Coaching Settings", "makeup_credit_validity_days") or 60
			)
			self.expires_on = add_days(self.issued_on, validity)

	@frappe.whitelist()
	def redeem(self, session: str) -> str:
		"""Use this credit for a makeup class session."""
		if self.status != "Open":
			frappe.throw(_("Credit is {0} and cannot be redeemed").format(self.status))
		if self.expires_on and getdate(self.expires_on) < getdate(today()):
			self.status = "Expired"
			self.save(ignore_permissions=True)
			frappe.throw(_("Credit expired on {0}").format(self.expires_on))
		self.status = "Used"
		self.used_in_session = session
		self.used_on = now_datetime()
		self.save(ignore_permissions=True)
		return self.name


def issue_credit(
	student: str, reason: str = "Absent", attendance: str | None = None
) -> str | None:
	"""Issue a makeup credit (respects the Coaching Settings toggle)."""
	if not cint(frappe.db.get_single_value("Coaching Settings", "auto_issue_makeup_credits")):
		return None
	existing = None
	if attendance:
		existing = frappe.db.exists("Makeup Credit", {"attendance": attendance})
		if existing:
			return existing
	credit = frappe.new_doc("Makeup Credit")
	credit.student = student
	credit.reason = reason
	credit.attendance = attendance
	credit.issued_on = today()
	credit.insert(ignore_permissions=True)
	return credit.name


def expire_stale_credits() -> int:
	"""Daily job: expire credits past their validity date."""
	expired = frappe.get_all(
		"Makeup Credit",
		filters={"status": "Open", "expires_on": ["<", today()]},
		pluck="name",
	)
	for name in expired:
		frappe.db.set_value("Makeup Credit", name, "status", "Expired")
	if expired:
		frappe.db.commit()
	return len(expired)
