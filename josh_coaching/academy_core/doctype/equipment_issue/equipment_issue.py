# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, today


class EquipmentIssue(Document):
	def validate(self):
		self._target_must_exist()
		if self.status == "Issued":
			self._stock_available()
		if self.status in ("Returned", "Damaged", "Lost") and not self.return_date:
			self.return_date = today()

	def _target_must_exist(self):
		if not self.student and not self.trainer:
			frappe.throw(_("Issue must be made to a Student or a Trainer"))

	def _stock_available(self):
		equipment = frappe.get_doc("Equipment", self.equipment)
		issued = frappe.db.count(
			"Equipment Issue",
			{"equipment": self.equipment, "status": "Issued", "name": ["!=", self.name]},
		)
		if cint(equipment.total_qty) and issued >= cint(equipment.total_qty):
			frappe.throw(
				_("No stock available for {0} ({1}/{2} issued)").format(
					equipment.equipment_name, issued, equipment.total_qty
				)
			)

	def on_update(self):
		if frappe.db.exists("Equipment", self.equipment):
			equipment = frappe.get_doc("Equipment", self.equipment)
			equipment.update_stock_counts()
			equipment.save(ignore_permissions=True)

	@frappe.whitelist()
	def mark_returned(self, condition: str | None = None, deposit_refunded: int = 0) -> str:
		self.status = "Returned"
		self.return_date = today()
		if condition:
			self.condition_notes = condition
		self.deposit_refunded = cint(deposit_refunded)
		self.save(ignore_permissions=True)
		return self.name


def notify_overdue_returns() -> int:
	"""Daily job: remind managers about issues past their expected return date."""
	overdue = frappe.get_all(
		"Equipment Issue",
		filters={
			"status": "Issued",
			"expected_return_date": ["between", ["2000-01-01", add_days(today(), -1)]],
		},
		fields=["name", "equipment", "student"],
	)
	for row in overdue:
		student_name = frappe.db.get_value("Student", row.student, "student_name") if row.student else ""
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": _("Equipment overdue: {0}").format(row.equipment),
				"email_content": _("{0} was due back on {1}. Issued to: {2}").format(
					row.equipment, row.expected_return_date, student_name or _("trainer")
				),
				"type": "Alert",
				"document_type": "Equipment Issue",
				"document_name": row.name,
			}
		)
	return len(overdue)
