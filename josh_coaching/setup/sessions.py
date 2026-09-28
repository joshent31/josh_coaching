# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Session automation helpers: reminders and no-show auto marking."""

from __future__ import annotations

from datetime import datetime, timedelta

import frappe
from frappe.utils import add_days, cint, now_datetime, today


def send_session_reminders() -> int:
	"""Notify enrolled students (and the trainer) about tomorrow's sessions."""
	tomorrow = add_days(today(), 1)
	sessions = frappe.get_all(
		"Class Session",
		filters={"session_date": tomorrow, "status": "Scheduled", "docstatus": 0},
		fields=["name", "batch", "start_time", "end_time", "trainer", "venue"],
	)
	for s in sessions:
		recipients = {s.trainer} if s.trainer else set()
		recipients.update(
			frappe.get_all(
				"Enrollment",
				filters={"batch": s.batch, "status": "Active", "docstatus": 0},
				pluck="student_user",
			)
		)
		recipients.discard(None)
		for user in recipients:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": f"Session reminder: {s.batch} at {s.start_time}",
					"email_content": (
						f"Your session for batch {s.batch} is on {tomorrow} "
						f"from {s.start_time} to {s.end_time} at {s.venue or 'the venue'}."
					),
					"for_user": user,
					"type": "Reminder",
					"document_type": "Class Session",
					"document_name": s.name,
				}
			).insert(ignore_permissions=True)
	return len(sessions)


def auto_mark_noshow() -> int:
	"""Mark Scheduled sessions as No Show once start time passed by a margin.

	Only sessions with zero present students get flagged; a trainer may
	still be marking attendance inside the grace window.
	"""
	margin = cint(frappe.db.get_single_value("Coaching Settings", "no_show_grace_minutes") or 30)
	cutoff = (now_datetime() - timedelta(minutes=margin)).time()

	sessions = frappe.get_all(
		"Class Session",
		filters={
			"status": "Scheduled",
			"docstatus": 0,
			"session_date": ["<=", today()],
		},
		fields=["name", "session_date", "start_time"],
	)
	count = 0
	for s in sessions:
		if s.session_date == today() and s.start_time > cutoff:
			continue
		if s.session_date < frappe.utils.getdate(today()) or s.start_time <= cutoff:
			frappe.db.set_value("Class Session", s.name, "status", "No Show")
			count += 1
	if count:
		frappe.db.commit()
	return count


def _minutes_until(dt: datetime) -> int:
	return int((dt - now_datetime()).total_seconds() // 60)
