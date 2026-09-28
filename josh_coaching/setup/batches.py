# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Batch automation helpers: expiry close-out, session generation, birthdays.

Each public function is idempotent and safe to run repeatedly from the
scheduler or manually from the console.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, today


def close_expired_batches() -> int:
	"""Mark Active batches whose end_date has passed as Completed."""
	expired = frappe.get_all(
		"Batch",
		filters={
			"status": "Active",
			"end_date": ["<", today()],
			"docstatus": 0,
		},
		pluck="name",
	)
	for name in expired:
		frappe.db.set_value("Batch", name, "status", "Completed")
	if expired:
		frappe.db.commit()
	return len(expired)


def generate_sessions_for_batch(batch: str, days_ahead: int = 7) -> list[str]:
	"""Create Class Sessions for a batch from its schedule lines.

	Skips (batch, date, start_time) combinations that already have a
	non-cancelled session, so it is safe to run repeatedly.
	"""
	batch_doc = frappe.get_doc("Batch", batch)
	if batch_doc.status not in ("Active", "Upcoming"):
		frappe.throw(_("Batch {0} is not active").format(batch))

	start = today()
	end = add_days(start, cint(days_ahead))
	created = []

	for line in batch_doc.get("schedule", []):
		date = start
		while date <= end:
			if line.day_of_week == frappe.utils.getdate(date).strftime("%A") and not _session_exists(
				batch, date, line.start_time
			):
					doc = frappe.new_doc("Class Session")
					doc.batch = batch
					doc.program = batch_doc.program
					doc.session_date = date
					doc.start_time = line.start_time
					doc.end_time = line.end_time
					doc.trainer = batch_doc.trainer
					doc.venue = batch_doc.venue
					doc.status = "Scheduled"
					doc.insert(ignore_permissions=True)
					created.append(doc.name)
			date = add_days(date, 1)
	return created


def _session_exists(batch: str, date: str, start_time) -> bool:
	return bool(
		frappe.db.exists(
			"Class Session",
			{
				"batch": batch,
				"session_date": date,
				"start_time": start_time,
				"status": ["!=", "Cancelled"],
			},
		)
	)


def notify_upcoming_birthdays(days_ahead: int = 3) -> int:
	"""Queue birthday alerts for students, sent to Academy Managers."""
	days_ahead = cint(days_ahead)
	count = 0
	for student in frappe.get_all(
		"Student",
		filters={"status": "Active", "date_of_birth": ["is", "set"]},
		fields=["name", "first_name", "last_name", "date_of_birth"],
	):
		dob = frappe.utils.getdate(student.date_of_birth)
		upcoming = dob.replace(year=frappe.utils.getdate(today()).year)
		delta = date_diff(upcoming, today())
		if 0 <= delta <= days_ahead:
			_notify_managers(
				subject=_("Upcoming birthday: {0} {1}").format(
					student.first_name, student.last_name or ""
				),
				message=_("{0} turns a year older in {1} day(s).").format(
					student.first_name, delta
				),
				user=student.name,
			)
			count += 1
	return count


def _notify_managers(subject: str, message: str, user: str | None = None):
	recipients = frappe.get_all(
		"Has Role",
		filters={"role": "Academy Manager", "parenttype": "User"},
		pluck="parent",
	)
	if not recipients:
		recipients = ["Administrator"]
	for recipient in set(recipients):
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"email_content": message,
				"for_user": recipient,
				"type": "Alert",
				"document_type": "Student",
				"document_name": user,
			}
		).insert(ignore_permissions=True)
