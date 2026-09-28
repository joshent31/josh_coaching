# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, today


class StudentDocument(Document):
	def validate(self):
		if self.status == "Received" and not self.attached_document:
			frappe.throw(_("Attach the file before marking as Received"))


def notify_expiring_documents(days_ahead: int = 14) -> int:
	"""Daily job: flag expiring/expired docs and alert managers."""
	expiring = frappe.get_all(
		"Student Document",
		filters={
			"status": ["in", ["Received", "Verified"]],
			"expiry_date": ["between", [today(), add_days(today(), days_ahead)]],
		},
		fields=["name", "student", "student_name", "document_type", "expiry_date"],
	)
	expired = frappe.get_all(
		"Student Document",
		filters={"status": ["in", ["Received", "Verified"]], "expiry_date": ["<", today()]},
		pluck="name",
	)
	for row in expired:
		frappe.db.set_value("Student Document", row, "status", "Expired")
	if expired:
		frappe.db.commit()

	from josh_coaching.setup.batches import _notify_managers

	if expiring:
		_notify_managers(
			subject=_("{0} student documents expiring soon").format(len(expiring)),
			message=_("Documents expiring within {0} days: {1}").format(
				days_ahead,
				", ".join(f"{d.student_name} ({d.document_type})" for d in expiring[:10]),
			),
		)
	return len(expiring) + len(expired)
