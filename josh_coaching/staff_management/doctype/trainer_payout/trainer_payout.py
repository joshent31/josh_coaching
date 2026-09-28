# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, time_diff_in_hours


class TrainerPayout(Document):
	def validate(self):
		if getdate(self.period_to) < getdate(self.period_from):
			frappe.throw(_("Period To cannot be before Period From"))
		self.calculate()

	def calculate(self):
		trainer_doc = frappe.get_doc("Coach", self.trainer)
		self.currency = trainer_doc.currency if trainer_doc.get("currency") else self.currency

		sessions = frappe.get_all(
			"Class Session",
			filters={
				"trainer": self.trainer,
				"status": "Completed",
				"session_date": ["between", [self.period_from, self.period_to]],
			},
			fields=["start_time", "end_time"],
		)
		self.sessions_taken = len(sessions)
		self.hours_taught = flt(
			sum(time_diff_in_hours(s.end_time, s.start_time) or 0 for s in sessions), 2
		)

		model = trainer_doc.payment_model or "Monthly Salary"
		rate = flt(trainer_doc.hourly_rate)
		if model == "Per Session":
			self.base_amount = flt(self.sessions_taken * rate)
		elif model in ("Hourly", "Revenue Share"):
			self.base_amount = flt(self.hours_taught * rate)
		else:  # Monthly Salary — use Employee salary via ERPNext if linked
			self.base_amount = 0
		self.net_payable = flt(self.base_amount + flt(self.manual_adjustment or 0))
		if self.status == "Draft":
			self.status = "Calculated"


def getdate(d):
	from frappe.utils import getdate as _g

	return _g(d)
