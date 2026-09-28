# Copyright (c) 2026, Josh Enterprises and contributors
# For license information, please see license.txt

"""Single daily / hourly scheduler entry dispatching each area's job."""


def daily():
	from josh_coaching.fees_management.fee_invoice import daily_overdue_escalation
	from josh_coaching.setup import batches, billing, sessions

	daily_overdue_escalation()
	billing.generate_recurring_invoices()
	billing.apply_late_fees()
	batches.close_expired_batches()
	batches.notify_upcoming_birthdays()
	sessions.send_session_reminders()

	from josh_coaching.academy_core.doctype.lead_inquiry.lead_inquiry import (
		notify_due_followups,
	)
	from josh_coaching.student_management.makeup_credit import expire_stale_credits

	notify_due_followups()
	expire_stale_credits()


def hourly():
	from josh_coaching.setup.sessions import auto_mark_noshow

	auto_mark_noshow()
