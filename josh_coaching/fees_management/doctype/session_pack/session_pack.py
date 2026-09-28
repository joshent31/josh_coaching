# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, today

UNLIMITED = "Monthly Unlimited"


class SessionPack(Document):
	def validate(self):
		if self.pack_type == UNLIMITED:
			self.total_sessions = 0
		if not self.expires_on and self.purchase_date:
			days = 30 if self.pack_type == UNLIMITED else 90
			self.expires_on = add_days(self.purchase_date, days)
		self._sync_counts()

	def _sync_counts(self):
		if self.pack_type == UNLIMITED:
			self.sessions_remaining = -1  # sentinel: unlimited
			return
		self.sessions_remaining = max(cint(self.total_sessions) - cint(self.sessions_used), 0)
		if self.sessions_remaining == 0 and self.status == "Active":
			self.status = "Exhausted"

	@frappe.whitelist()
	def consume(self) -> str:
		"""Consume one session from this pack."""
		if self.status != "Active":
			frappe.throw(_("Pack is {0}").format(self.status))
		if self.expires_on and getdate(self.expires_on) < getdate(today()):
			self.db_set("status", "Expired")
			frappe.throw(_("Pack expired on {0}").format(self.expires_on))
		if self.pack_type != UNLIMITED:
			if cint(self.sessions_remaining) <= 0:
				frappe.throw(_("Pack has no sessions remaining"))
			self.sessions_used = cint(self.sessions_used) + 1
			self.sessions_remaining = cint(self.total_sessions) - self.sessions_used
			if self.sessions_remaining == 0:
				self.status = "Exhausted"
		self.save(ignore_permissions=True)
		return self.name


def expire_stale_packs() -> int:
	"""Daily job: expire packs past validity."""
	expired = frappe.get_all(
		"Session Pack",
		filters={"status": "Active", "expires_on": ["<", today()]},
		pluck="name",
	)
	for name in expired:
		frappe.db.set_value("Session Pack", name, "status", "Expired")
	if expired:
		frappe.db.commit()
	return len(expired)
